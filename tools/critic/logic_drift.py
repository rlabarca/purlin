"""Logic drift engine: LLM-based semantic alignment analysis.

Compares Gherkin scenario text against test function bodies using an LLM
to determine if the test actually verifies the scenario's intent.

Produces per-pair verdicts: ALIGNED | PARTIAL | DIVERGENT.
Results are cached by SHA-256 hash of (scenario_body, test_body).
"""

import hashlib
import json
import os

# Conditional import -- only needed when LLM is enabled
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    anthropic = None
    HAS_ANTHROPIC = False

DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache')

SYSTEM_PROMPT = (
    'You are a test alignment auditor. Given a Gherkin scenario and a test '
    'function, determine if the test verifies the scenario\'s intent.\n\n'
    'Respond with ONLY a JSON object (no markdown fences, no extra text):\n'
    '{"verdict": "ALIGNED or PARTIAL or DIVERGENT", "reasoning": "brief explanation"}\n\n'
    '- ALIGNED: The test fully verifies the scenario\'s intent.\n'
    '- PARTIAL: The test covers some but not all aspects of the scenario.\n'
    '- DIVERGENT: The test does not verify the scenario\'s intent at all.'
)

VALID_VERDICTS = frozenset({'ALIGNED', 'PARTIAL', 'DIVERGENT'})


def _cache_key(scenario_body, test_body):
    """Generate SHA-256 cache key from scenario + test bodies."""
    combined = scenario_body + '\n---\n' + test_body
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def _resolve_cache_dir(project_root):
    """Resolve the LLM verdict cache directory.

    Uses <project_root>/.purlin/cache/logic_drift_cache/ per submodule
    safety contract §2.12.  Falls back to script-local .cache/ only if
    project_root is not provided.
    """
    if project_root:
        return os.path.join(project_root, '.purlin', 'cache', 'logic_drift_cache')
    return DEFAULT_CACHE_DIR


def _read_cache(cache_dir, cache_key):
    """Read cached verdict. Returns dict or None."""
    path = os.path.join(cache_dir, f'{cache_key}.json')
    if os.path.isfile(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            pass
    return None


def _write_cache(cache_dir, cache_key, data):
    """Write verdict to cache."""
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f'{cache_key}.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def _call_llm(client, scenario_body, test_body, model):
    """Call the LLM and parse the verdict.

    Returns dict with 'verdict' and 'reasoning', or None on failure.
    """
    user_prompt = (
        '## Gherkin Scenario\n'
        f'{scenario_body}\n\n'
        '## Test Function\n'
        f'{test_body}\n\n'
        'Does this test verify the intent of this scenario? '
        'Respond with JSON only.'
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': user_prompt}],
        )

        text = response.content[0].text.strip()
        # Strip markdown code fences if present
        if text.startswith('```'):
            lines = text.split('\n')
            text = '\n'.join(lines[1:-1]) if len(lines) > 2 else text
            text = text.strip()

        result = json.loads(text)
        verdict = result.get('verdict', '').upper()
        if verdict not in VALID_VERDICTS:
            return None
        return {
            'verdict': verdict,
            'reasoning': result.get('reasoning', ''),
        }
    except Exception:
        return None


def run_logic_drift(pairs, project_root, feature_stem, tools_root, model):
    """Run logic drift analysis on scenario-test pairs.

    Args:
        pairs: list of dicts, each with:
            - scenario_title (str)
            - scenario_body (str): Gherkin Given/When/Then text
            - test_functions (list of {'name': str, 'body': str})
        project_root: absolute path to project root
        feature_stem: feature file stem (e.g., 'critic_tool')
        tools_root: relative path to tools directory
        model: LLM model identifier (e.g., 'claude-sonnet-4-20250514')

    Returns:
        dict with 'status' ('PASS'|'WARN'|'FAIL'), 'pairs', 'detail'
    """
    if not HAS_ANTHROPIC:
        return {
            'status': 'WARN',
            'pairs': [],
            'detail': 'Logic drift skipped: anthropic package not installed.',
        }

    if not pairs:
        return {
            'status': 'PASS',
            'pairs': [],
            'detail': 'No scenario-test pairs to analyze.',
        }

    # Create client once for all pairs
    try:
        client = anthropic.Anthropic()
    except Exception:
        return {
            'status': 'WARN',
            'pairs': [],
            'detail': 'Logic drift skipped: failed to initialize Anthropic client.',
        }

    cache_dir = _resolve_cache_dir(project_root)

    results = []
    has_divergent = False
    has_partial = False
    skipped = 0

    for pair in pairs:
        scenario_title = pair['scenario_title']
        scenario_body = pair['scenario_body']

        for test_func in pair['test_functions']:
            test_name = test_func['name']
            test_body = test_func['body']

            # Check cache first
            key = _cache_key(scenario_body, test_body)
            cached = _read_cache(cache_dir, key)

            if cached and cached.get('verdict') in VALID_VERDICTS:
                verdict_data = cached
            else:
                verdict_data = _call_llm(client, scenario_body, test_body, model)
                if verdict_data is None:
                    skipped += 1
                    results.append({
                        'scenario': scenario_title,
                        'test': test_name,
                        'verdict': 'SKIPPED',
                        'reasoning': 'LLM call failed or returned invalid response.',
                    })
                    continue
                _write_cache(cache_dir, key, verdict_data)

            verdict = verdict_data['verdict']
            if verdict == 'DIVERGENT':
                has_divergent = True
            elif verdict == 'PARTIAL':
                has_partial = True

            results.append({
                'scenario': scenario_title,
                'test': test_name,
                'verdict': verdict,
                'reasoning': verdict_data.get('reasoning', ''),
            })

    # Determine overall status: FAIL > WARN > PASS
    if has_divergent:
        status = 'FAIL'
    elif has_partial or skipped > 0:
        status = 'WARN'
    else:
        status = 'PASS'

    total = len(results)
    aligned = sum(1 for r in results if r['verdict'] == 'ALIGNED')
    detail_parts = [f'{aligned}/{total} pairs ALIGNED']
    if skipped:
        detail_parts.append(f'{skipped} skipped (API error)')

    return {
        'status': status,
        'pairs': results,
        'detail': '. '.join(detail_parts),
    }
