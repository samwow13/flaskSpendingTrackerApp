# Spending Tracker Style Guide

This document outlines the design system and UI components used throughout the Spending Tracker application to ensure consistency and a premium user experience.

## Color Palette

### Primary Colors
- **Primary Blue**: #4a6cf7 - Used for primary actions, links, and highlights
- **Secondary Blue**: #3b5de7 - Used for hover states and gradients
- **Dark Blue**: #2c3e50 - Used for headers and footers

### Neutral Colors
- **Background**: #f8f9fa - Main background color
- **Light Gray**: #dee2e6 - Borders and dividers
- **Medium Gray**: #6c757d - Secondary text and icons
- **Dark Gray**: #495057 - Primary text
- **White**: #ffffff - Card backgrounds and text on dark backgrounds

## Typography

### Font Family
```css
font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
```

### Font Weights
- **Regular**: 400 - Body text
- **Medium**: 500 - Buttons, labels
- **Semibold**: 600 - Card titles, section headings
- **Bold**: 700 - Page titles

### Font Sizes
- **Small**: 0.875rem (14px) - Helper text, captions
- **Base**: 1rem (16px) - Body text
- **Large**: 1.25rem (20px) - Subheadings
- **XL**: 1.5rem (24px) - Section headings
- **XXL**: 2rem (32px) - Page titles

## Components

### Cards

#### Premium Card
Used for main content sections and forms.

```html
<div class="card shadow-sm premium-card">
    <div class="card-header bg-gradient">
        <h2 class="card-title mb-0">Card Title</h2>
    </div>
    <div class="card-body p-4">
        <!-- Content goes here -->
    </div>
</div>
```

### Buttons

#### Primary Button
Used for main actions like saving or submitting.

```html
<button type="submit" class="btn btn-primary px-4">Save</button>
```

#### Secondary Button
Used for secondary actions like canceling or going back.

```html
<a href="#" class="btn btn-outline-secondary">Cancel</a>
```

### Form Elements

#### Text Inputs
```html
<div class="mb-3">
    <label for="inputField" class="form-label fw-medium">Label</label>
    <input type="text" class="form-control" id="inputField" placeholder="Placeholder text">
</div>
```

#### Input Groups
```html
<div class="input-group">
    <span class="input-group-text"><i class="bi bi-currency-dollar"></i></span>
    <input type="number" class="form-control form-control-lg" placeholder="0.00">
</div>
```

#### Select Dropdowns
```html
<div class="mb-3">
    <label for="selectField" class="form-label fw-medium">Label</label>
    <select class="form-select form-select-lg" id="selectField">
        <option value="" disabled selected>Select an option</option>
        <option value="1">Option 1</option>
    </select>
</div>
```

#### Toggle Switches
```html
<div class="form-check form-switch mb-3">
    <input class="form-check-input" type="checkbox" id="toggleSwitch">
    <label class="form-check-label" for="toggleSwitch">Toggle Label</label>
</div>
```

## Icons

The application uses Bootstrap Icons. Include the following in the head section:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
```

Common icons used:
- `bi-currency-dollar` - For currency/amount fields
- `bi-calendar-date` - For date fields
- `bi-repeat` - For recurring items
- `bi-exclamation-triangle-fill` - For warnings/errors

## Layout Guidelines

### Spacing
- Use Bootstrap's spacing utilities (m-*, p-*) for consistent spacing
- Standard margins between sections: 1.5rem (mb-4)
- Standard padding inside containers: 1.5rem (p-4)

### Responsive Breakpoints
- **Small**: < 576px
- **Medium**: ≥ 576px
- **Large**: ≥ 768px
- **Extra Large**: ≥ 992px
- **Extra Extra Large**: ≥ 1200px

### Grid System
Use Bootstrap's grid system with appropriate column sizes:

```html
<div class="row g-3">
    <div class="col-md-6"><!-- Half width on medium screens and up --></div>
    <div class="col-md-6"><!-- Half width on medium screens and up --></div>
</div>
```

## Animation Guidelines

- Use subtle transitions for hover states (0.2-0.3s)
- Avoid excessive animations that might distract users
- Recommended transitions:
  ```css
  transition: all 0.3s ease;
  ```

## Accessibility Guidelines

- Maintain color contrast ratios of at least 4.5:1 for text
- Always include proper labels for form elements
- Use aria attributes where appropriate
- Ensure keyboard navigation works properly
- Include descriptive alt text for images

---

This style guide should be followed when developing new features or modifying existing ones to maintain a consistent, premium look and feel throughout the application.
