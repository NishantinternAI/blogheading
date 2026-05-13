# content_engine/image_module/validator.py

from PIL import Image
import os

#  Expected blog image size
BLOG_DIMENSIONS = (1200, 630)

# Base directory (image_module folder)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Correct templates path
TEMPLATES_BASE = os.path.abspath(
    os.path.join(BASE_DIR, "../templates")
)


#  Custom Error
class TemplateDimensionError(Exception):
    pass


# Validate single template
def validate_template(image_path: str, image_type: str = 'blog') -> bool:
    """
    Validates that a template image matches required dimensions.
    """

    expected = BLOG_DIMENSIONS

    with Image.open(image_path) as img:
        actual_w, actual_h = img.size
        expected_w, expected_h = expected

        if (actual_w, actual_h) != (expected_w, expected_h):
             print(f"[WARNING] Resizing template: {image_path}")
             resized = img.resize((expected_w, expected_h))
             resized.save(image_path)
           

    return True


# Validate all templates
def validate_all_templates(templates_base: str = None) -> dict:
    """
    Scans entire templates folder and validates all images
    """

    if templates_base is None:
        templates_base = TEMPLATES_BASE

    report = {'passed': [], 'failed': []}

    for category in os.listdir(templates_base):
        cat_path = os.path.join(templates_base, category)

        if not os.path.isdir(cat_path):
            continue

        for fname in os.listdir(cat_path):
            if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue

            fpath = os.path.join(cat_path, fname)

            try:
                validate_template(fpath)
                report['passed'].append(f'{category}/{fname}')

            except TemplateDimensionError as e:
                report['failed'].append({
                    'file': f'{category}/{fname}',
                    'reason': str(e)
                })

    return report


#  Run from terminal
if __name__ == '__main__':
    report = validate_all_templates()

    print(f"Passed: {len(report['passed'])} images")

    if report['failed']:
        print(f"\nFAILED: {len(report['failed'])} images need fixing:\n")

        for f in report['failed']:
            print(f"- {f['file']}")
            print(f"  {f['reason']}\n")
    else:
        print("🎉 All templates are correctly sized. Ready to use.")