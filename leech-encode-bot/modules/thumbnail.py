import os

from PIL import Image

import config


def center_crop_square(image_path: str, output_path: str = None) -> str:
    """
    Crops a square box out of the exact center of the image using pixel
    math: box edge = min(width, height), positioned so it's centered on
    both axes. No stretching or resizing, just a true center crop.
    """
    img = Image.open(image_path).convert("RGB")
    width, height = img.size

    box_size = min(width, height)
    left = (width - box_size) // 2
    top = (height - box_size) // 2
    right = left + box_size
    bottom = top + box_size

    cropped = img.crop((left, top, right, bottom))

    if output_path is None:
        output_path = image_path

    cropped.save(output_path, "JPEG")
    return output_path


def save_user_thumbnail(user_id: int, source_image_path: str) -> str:
    """
    Crops the uploaded image to a centered square and stores it as this
    user's thumbnail, applied to every file they leech until cleared.
    """
    dest_path = os.path.join(config.THUMB_DIR, f"{user_id}.jpg")
    return center_crop_square(source_image_path, dest_path)


def get_user_thumbnail_path(user_id: int):
    path = os.path.join(config.THUMB_DIR, f"{user_id}.jpg")
    return path if os.path.exists(path) else None


def clear_user_thumbnail(user_id: int):
    path = os.path.join(config.THUMB_DIR, f"{user_id}.jpg")
    if os.path.exists(path):
        os.remove(path)
