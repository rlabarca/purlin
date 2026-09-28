package cart

import "errors"

func Total(a, b int) int { return a + b }

func Parse(s string) (int, error) {
	if s == "" {
		return 0, errors.New("empty")
	}
	return len(s), nil
}
