# Feature: Feedback Form

> Label: "UI: Feedback Form"
> Category: "UI"
> Owner: PM
> Prerequisite: features/arch_web_app.md
> Prerequisite: features/design_visual_standards.md
> Web Test: http://localhost:3000
> Web Start: npm run dev

## 1. Overview

A "Send feedback" modal served as the single page of the local web app. Users select an issue type, optionally add details and an attachment, then submit. On submission the server appends a JSON record to `data/feedback.json` and saves any uploaded file to `uploads/`. The modal matches the Figma design: white card with rounded corners, a close (X) button, a dropdown, a textarea, a file upload zone, and Cancel / Submit actions in a grey footer.

---

## 2. Requirements

### 2.1 Issue Type Dropdown

- The dropdown MUST offer exactly three options: **Bug**, **Usability**, **Feature Request**.
- The dropdown MUST display "Select..." as the default placeholder (unselected state).
- Submitting without selecting an issue type MUST show a validation error and prevent submission.

### 2.2 Details Textarea

- The textarea is optional; the user may submit without entering text.
- Placeholder text: "Add any details here ..."
- The textarea MUST be vertically resizable.

### 2.3 Attachments

- Clicking "Upload file" MUST open the device's native file picker.
- Only one file may be attached per submission.
- Files larger than 5MB MUST be rejected with an inline error message.
- Accepted file MUST be displayed by filename below the upload button.

### 2.4 Submission

- Clicking **Submit** MUST POST the form data (issue type, details, attachment) to `POST /feedback`.
- The server MUST append a JSON object to `data/feedback.json` containing:
  - `id`: a UUID or timestamp-based unique identifier
  - `timestamp`: ISO 8601 UTC string
  - `issueType`: one of "Bug" | "Usability" | "Feature Request"
  - `details`: string (may be empty)
  - `attachmentPath`: relative path within `uploads/` if a file was attached, otherwise `null`
- The Submit button MUST use `--color-supplementary-amber` (`#F59E0B`) as its background color.
- On success the modal MUST display a confirmation message: "Thank you! Your feedback has been submitted."
- On server error the modal MUST display: "Something went wrong. Please try again."

### 2.5 Cancel / Close

- Clicking **Cancel** or the **X** button MUST reset all form fields to their default state.
- No data is saved on cancel.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Successful submission with all fields

    Given the feedback form is open
    When the user selects "Bug" from the issue type dropdown
    And the user enters "Reproducible crash on load" in the details textarea
    And the user attaches a file under 5MB
    And the user clicks Submit
    Then the server returns HTTP 200
    And a new entry is appended to data/feedback.json with issueType "Bug"
    And the confirmation message is displayed

#### Scenario: Submission blocked when no issue type selected

    Given the feedback form is open
    And no issue type has been selected
    When the user clicks Submit
    Then no POST request is sent
    And a validation error is displayed near the dropdown

#### Scenario: File over 5MB is rejected

    Given the feedback form is open
    When the user attempts to attach a file larger than 5MB
    Then an inline error message is displayed
    And the file is not attached

#### Scenario: Cancel resets the form

    Given the user has selected "Usability" and typed details
    When the user clicks Cancel
    Then all fields are reset to their default state
    And no data is saved

### Manual Scenarios (Human Verification Required)

#### Scenario: Visual match to Figma design

    Given the feedback form is rendered in a browser
    When the tester compares it to the Figma reference screenshot
    Then the modal header, dropdown, textarea, attachment zone, and footer visually match the design

---

## Visual Specification

> **Design Anchor:** features/design_visual_standards.md
> **Figma File:** TEZI0T6lObCJrC9mkmZT8v
> **Figma Node:** 7:81
> **Figma Status:** Design

### Screen: Feedback Modal

- **Reference:** Figma node 7:81 (modal-test)
- **Processed:** 2026-03-24
- **Token Map:**
  - `--color/shades/shade-white` -> `--color-white`
  - `--color/neutral/neutral-800` -> `--color-neutral-800`
  - `--color/neutral/neutral-100` -> `--color-neutral-100`
  - `--color/neutral/neutral-300` -> `--color-neutral-300`
  - `--color/supplementary/amber` -> `--color-supplementary-amber`
  - `--background/bg-elevated` -> `--color-bg-elevated`
  - `--border/border-primary` -> `--border-primary`
  - `--text/text-primary` -> `--text-primary`
  - `--text/text-secondary` -> `--text-secondary`
  - `--text/text-white` -> `--text-white`
- [ ] Modal is a white rounded card (border-radius 16px), width 428px, centered on a neutral or overlay background
- [ ] Header: "Send feedback" in Inter Semi Bold 16px (`--text-primary`), left-aligned; X close icon right-aligned; bottom border `--border-primary`
- [ ] Issue type label: "What type of issue do you wish to report?" in Inter Medium 14px (`--text-primary`)
- [ ] Dropdown: bg `--color-bg-elevated`, border `--border-primary`, border-radius 8px, height 36px, width 380px, shadow `0 1px 2px rgba(0,0,0,0.1)`; shows chevron-down icon on right
- [ ] Details label: "Please provide details: (optional)" in Inter Medium 14px (`--text-primary`)
- [ ] Textarea: bg `--color-bg-elevated`, border `--border-primary`, border-radius 8px, height 65px, shadow `0 4px 8px rgba(0,0,0,0.1)`, resize handle visible bottom-right; placeholder "Add any details here ..."
- [ ] Attachments label: "Attachments:" in Inter Medium 14px (`--text-primary`)
- [ ] Attachment zone: bg `--color-neutral-100`, dashed border `--color-neutral-300`, border-radius 12px, height 110px, width 380px, centered content
- [ ] "Max file size: 5MB" caption: Inter Regular 12px (`--text-secondary`)
- [ ] "Upload file" button: bg `--color-white`, border `--color-neutral-800`, border-radius 8px, height 32px, upload icon + label Inter Medium 14px (`--text-primary`)
- [ ] Footer: bg `--color-neutral-100`, padding 16px 24px, rounded bottom corners (16px)
- [ ] Footer info text: "We'll include your name and current session details with this submission." in Inter Regular 12px (`--text-secondary`), left-aligned
- [ ] "Cancel" button: bg `--color-white`, border `--color-supplementary-purple-500`, border-radius 8px, height 40px, Inter Medium 14px (`--text-primary`)
- [ ] "Submit" button: bg `--color-supplementary-amber` (`#F59E0B`), border-radius 8px, height 40px, Inter Medium 14px (`--text-white`)
