"""HTML manipulation utilities."""

import base64
import mimetypes
from logging import getLogger
from pathlib import Path

logger = getLogger(__name__)


def data_uri_for_local_image(template_dir: Path, rel_path: str) -> str | None:
    """Convert local image to data URI for embedding in HTML.

    Args:
        template_dir: Base directory for templates
        rel_path: Relative path to the image (e.g., './images/logo.png')

    Returns:
        Data URI string or None if conversion fails
    """
    # Support ./images/... or images/...
    rel = rel_path.lstrip("./")
    img_path = template_dir / rel

    if not img_path.exists():
        try:
            root_templates = template_dir.parent.parent  # .../templates
            alt_path = root_templates / "assets" / rel
            if alt_path.exists():
                img_path = alt_path
            else:
                return None
        except Exception:
            return None

    try:
        data = img_path.read_bytes()
        mime, _ = mimetypes.guess_type(str(img_path))
        if not mime:
            mime = "image/jpeg"
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception as e:
        logger.exception("Failed to inline image %s: %s", img_path, e)
        return None


def inline_css(html: str, css_content: str) -> str:
    """Inline CSS content into HTML by replacing link tags.

    Args:
        html: HTML content
        css_content: CSS content to inline

    Returns:
        HTML with inlined CSS
    """
    if not css_content:
        return html

    style_tag = f"<style>\n{css_content}\n</style>"

    # Replace various forms of CSS link tags
    html = html.replace('<link rel="stylesheet" href="styles.css">', style_tag)
    html = html.replace('<link rel="stylesheet" href="./styles.css">', style_tag)

    return html


def inline_local_images(html: str, template_dir: Path) -> str:
    """Inline local images into HTML as data URIs.

    Args:
        html: HTML content
        template_dir: Base directory for templates

    Returns:
        HTML with inlined images
    """
    markers = [
        'src="./images/',
        'src="images/',
    ]

    for marker in markers:
        start = 0
        while True:
            idx = html.find(marker, start)
            if idx == -1:
                break

            # Find the opening and closing quotes of the src attribute
            q1 = html.find('"', idx)  # the first quote after src=
            q2 = html.find('"', q1 + 1)

            if q1 == -1 or q2 == -1:
                break

            path_val = html[q1 + 1 : q2]
            data_uri = data_uri_for_local_image(template_dir, path_val)

            if data_uri:
                html = html[: q1 + 1] + data_uri + html[q2:]
                start = q1 + 1 + len(data_uri)
            else:
                start = q2 + 1

    return html


def inline_assets(html: str, template_dir: Path, css_content: str) -> str:
    """Inline all assets (CSS and images) into HTML.

    Args:
        html: HTML content
        template_dir: Base directory for templates
        css_content: CSS content to inline

    Returns:
        HTML with all assets inlined
    """
    html = inline_css(html, css_content)
    html = inline_local_images(html, template_dir)

    logger.debug("HTML content after inlining assets: %s", html[:500])

    return html
