# content_engine/image_module/validator.py



from PIL import Image
import os

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_BASE = os.path.abspath(os.path.join(BASE_DIR, "../templates"))

# ── Expected sizes per image type ────────────────────────────
EXPECTED_SIZES = {
    "outer"     : (640,  480),
    "inner"     : (1920, 490),
    "instagram" : (1080, 1080),
}


def validate_template(image_path: str) -> bool:
    """
    Validates template exists and is readable.
    Does NOT resize — compositor handles sizing.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Template not found: {image_path}")

    with Image.open(image_path) as img:
        w, h = img.size
        print(f"[VALIDATE] {os.path.basename(image_path)} → {w}×{h} ✅")

    return True


def validate_all_templates(templates_base: str = None) -> dict:
    """
    Scans entire templates folder and reports sizes.
    Does NOT resize anything.
    """
    if templates_base is None:
        templates_base = TEMPLATES_BASE

    report = {'passed': [], 'failed': []}

    for category in os.listdir(templates_base):
        cat_path = os.path.join(templates_base, category)

        if not os.path.isdir(cat_path):
            continue

        for subfolder in ["outer", "inner"]:
            sub_path = os.path.join(cat_path, subfolder)

            if not os.path.isdir(sub_path):
                continue

            expected = EXPECTED_SIZES.get(subfolder)

            for fname in os.listdir(sub_path):
                if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue

                fpath = os.path.join(sub_path, fname)

                with Image.open(fpath) as img:
                    actual = img.size

                if expected and actual != expected:
                    print(f"[WARNING] {category}/{subfolder}/{fname} → {actual} (expected {expected})")
                    report['failed'].append({
                        'file'    : f'{category}/{subfolder}/{fname}',
                        'actual'  : actual,
                        'expected': expected
                    })
                else:
                    report['passed'].append(f'{category}/{subfolder}/{fname}')

    return report


if __name__ == '__main__':
    report = validate_all_templates()
    print(f"\nPassed : {len(report['passed'])} templates")
    print(f"Warning: {len(report['failed'])} wrong size (compositor will auto-resize)")

    for f in report['failed']:
        print(f"  - {f['file']} → {f['actual']} (expected {f['expected']})")

# from PIL import Image
# import os

# #  Expected blog image size
# BLOG_DIMENSIONS = (1200, 630)

# # Base directory (image_module folder)
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # Correct templates path
# TEMPLATES_BASE = os.path.abspath(
#     os.path.join(BASE_DIR, "../templates")
# )


# #  Custom Error
# class TemplateDimensionError(Exception):
#     pass


# # Validate single template
# def validate_template(image_path: str, image_type: str = 'blog') -> bool:
#     """
#     Validates that a template image matches required dimensions.
#     """

#     expected = BLOG_DIMENSIONS

#     with Image.open(image_path) as img:
#         actual_w, actual_h = img.size
#         expected_w, expected_h = expected

#         if (actual_w, actual_h) != (expected_w, expected_h):
#              print(f"[WARNING] Resizing template: {image_path}")
#              resized = img.resize((expected_w, expected_h))
#              resized.save(image_path)
           

#     return True


# # Validate all templates
# def validate_all_templates(templates_base: str = None) -> dict:
#     """
#     Scans entire templates folder and validates all images
#     """

#     if templates_base is None:
#         templates_base = TEMPLATES_BASE

#     report = {'passed': [], 'failed': []}

#     for category in os.listdir(templates_base):
#         cat_path = os.path.join(templates_base, category)

#         if not os.path.isdir(cat_path):
#             continue

#         for fname in os.listdir(cat_path):
#             if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
#                 continue

#             fpath = os.path.join(cat_path, fname)

#             try:
#                 validate_template(fpath)
#                 report['passed'].append(f'{category}/{fname}')

#             except TemplateDimensionError as e:
#                 report['failed'].append({
#                     'file': f'{category}/{fname}',
#                     'reason': str(e)
#                 })

#     return report


# #  Run from terminal
# if __name__ == '__main__':
#     report = validate_all_templates()

#     print(f"Passed: {len(report['passed'])} images")

#     if report['failed']:
#         print(f"\nFAILED: {len(report['failed'])} images need fixing:\n")

#         for f in report['failed']:
#             print(f"- {f['file']}")
#             print(f"  {f['reason']}\n")
#     else:
#         print("🎉 All templates are correctly sized. Ready to use.")