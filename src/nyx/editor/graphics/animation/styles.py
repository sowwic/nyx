from nyx.editor.graphics.animation.glow_animation import GlowAnimation
from nyx.editor.graphics.animation.link_animation import LinkAnimation
from nyx.editor.graphics.animation.pulse_animation import PulseAnimation
from nyx.static.enums import LinkAnimationStyle

ANIMATION_CLASSES: dict[LinkAnimationStyle, type[LinkAnimation]] = {
    LinkAnimationStyle.PULSE: PulseAnimation,
    LinkAnimationStyle.GLOW: GlowAnimation,
}
"""Animation class of every style."""


def create_animation(style: LinkAnimationStyle) -> LinkAnimation:
    """Create the animation of a style.

    Args:
        style (LinkAnimationStyle): style of the animation.

    Returns:
        LinkAnimation: new animation.
    """
    return ANIMATION_CLASSES[style]()
