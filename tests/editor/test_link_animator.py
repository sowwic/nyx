import pytest
from PySide6 import QtCore

from nyx.editor.graphics.animation.link_animation import LinkAnimation
from nyx.editor.graphics.animation.link_animator import LinkAnimator, ViewArea
from nyx.editor.graphics.animation.pulse_animation import PulseAnimation

AREA = QtCore.QRectF(0, 0, 100, 100)
INSIDE = QtCore.QRectF(10, 10, 20, 20)
OUTSIDE = QtCore.QRectF(5000, 5000, 20, 20)


class StubLink:
    """Just what the animator needs of a graphics link."""

    def __init__(self, rect=INSIDE):
        self._rect = rect
        self.animations = {}
        self.updates = 0

    def sceneBoundingRect(self):
        return self._rect

    def add_animation(self, animation):
        self.animations[type(animation)] = animation

    def remove_animation(self, kind):
        self.animations.pop(kind, None)

    def update(self):
        self.updates += 1


class RecordingAnimation(LinkAnimation):
    SHAPE_SIZE = 10.0

    def __init__(self):
        self.times = []
        self.resets = 0

    def advance(self, seconds):
        self.times.append(seconds)

    def reset(self):
        self.resets += 1


class TinyAnimation(RecordingAnimation):
    SHAPE_SIZE = 1.0  # needs a big scale to be seen


class OtherAnimation(RecordingAnimation):
    pass


def make_animator(areas=None):
    return LinkAnimator(visible_areas=None if areas is None else lambda: areas)


# ======== Registry ========= #


def test_animator_runs_only_while_it_has_animations(qapp):
    animator = make_animator()
    link = StubLink()
    assert not animator.is_running

    animator.register(link, RecordingAnimation())
    assert animator.is_running

    animator.unregister(link)
    assert not animator.is_running


def test_register_puts_the_animation_on_the_link(qapp):
    animator = make_animator()
    link, animation = StubLink(), RecordingAnimation()

    animator.register(link, animation)

    assert link.animations == {RecordingAnimation: animation}
    assert animator.links == frozenset({link})
    assert animator.animations_of(link) == [animation]


def test_registering_a_kind_again_replaces_and_resets_the_old_one(qapp):
    animator = make_animator()
    link = StubLink()
    old, new = RecordingAnimation(), RecordingAnimation()
    animator.register(link, old)

    animator.register(link, new)

    assert old.resets == 1
    assert animator.animations_of(link) == [new]
    assert link.animations == {RecordingAnimation: new}


def test_unregister_one_kind_keeps_the_others(qapp):
    animator = make_animator()
    link = StubLink()
    keep, drop = RecordingAnimation(), OtherAnimation()
    animator.register(link, keep)
    animator.register(link, drop)

    animator.unregister(link, OtherAnimation)

    assert animator.animations_of(link) == [keep]
    assert drop.resets == 1
    assert OtherAnimation not in link.animations
    assert animator.is_running


def test_unregister_without_a_kind_releases_the_link(qapp):
    animator = make_animator()
    link = StubLink()
    animation = RecordingAnimation()
    animator.register(link, animation)

    animator.unregister(link)

    assert animator.links == frozenset()
    assert link.animations == {}
    assert animation.resets == 1


def test_clear_can_be_limited_to_a_kind(qapp):
    animator = make_animator()
    first, second = StubLink(), StubLink()
    for link in (first, second):
        animator.register(link, RecordingAnimation())
    animator.register(second, OtherAnimation())

    animator.clear(RecordingAnimation)

    assert animator.links == frozenset({second})
    assert animator.animations_of(second)[0].__class__ is OtherAnimation

    animator.clear()

    assert animator.links == frozenset()
    assert not animator.is_running


# ======== Ticks ========= #


def test_tick_advances_with_the_time_since_the_start(qapp):
    animator = make_animator()
    link, animation = StubLink(), RecordingAnimation()
    animator.register(link, animation)

    animator.tick(1500)
    animator.tick(2500)

    assert animation.times == [1.5, 2.5]
    assert link.updates == 2


def test_tick_updates_a_link_once_however_many_animations_it_has(qapp):
    animator = make_animator()
    link = StubLink()
    animator.register(link, RecordingAnimation())
    animator.register(link, OtherAnimation())

    animator.tick(1000)

    assert link.updates == 1


def test_tick_is_skipped_while_paused(qapp):
    animator = make_animator()
    link, animation = StubLink(), RecordingAnimation()
    animator.register(link, animation)

    animator.set_paused(True)
    assert animation.resets == 1  # hidden by the pause
    assert animator.is_paused
    assert not animator.is_running
    animator.tick(1000)
    assert animation.times == []

    animator.set_paused(False)
    animator.tick(1000)
    assert animation.times == [1.0]
    assert animator.is_running


# ======== Visibility ========= #


def test_only_animations_inside_a_visible_area_run(qapp):
    animator = make_animator([ViewArea(AREA, 1.0)])
    inside, outside = StubLink(INSIDE), StubLink(OUTSIDE)
    inside_animation, outside_animation = RecordingAnimation(), RecordingAnimation()
    animator.register(inside, inside_animation)
    animator.register(outside, outside_animation)

    animator.tick(1000)

    assert inside_animation.times == [1.0]
    assert outside_animation.times == []
    assert animator.active_links() == [inside]
    assert animator.is_animating


def test_nothing_runs_without_visible_areas(qapp):
    animator = make_animator([])
    animation = RecordingAnimation()
    animator.register(StubLink(), animation)

    animator.tick(1000)

    assert animation.times == []
    assert animator.is_running  # the timer still runs
    assert not animator.is_animating


def test_an_animation_too_small_to_see_is_skipped(qapp):
    animator = make_animator([ViewArea(AREA, 0.1)])
    link = StubLink()
    seen, unseen = TinyAnimation(), RecordingAnimation()
    animator.register(link, seen)
    animator.register(link, unseen)

    animator.tick(1000)

    # 1 unit at 10% is 0.1 px, 10 units at 10% is 1 px, both are too small here.
    assert seen.times == []
    assert unseen.times == []
    assert not animator.is_animating


def test_each_animation_is_judged_by_its_own_size(qapp):
    animator = make_animator([ViewArea(AREA, 0.5)])
    link = StubLink()
    big, small = RecordingAnimation(), TinyAnimation()  # 10 units / 1 unit
    animator.register(link, big)
    animator.register(link, small)

    animator.tick(1000)

    assert big.times == [1.0]  # 10 units at 50% is 5 px
    assert small.times == []  # 1 unit at 50% is 0.5 px


def test_a_link_in_any_of_the_areas_runs(qapp):
    zoomed_out = ViewArea(QtCore.QRectF(0, 0, 100, 100), 0.05)
    zoomed_in = ViewArea(QtCore.QRectF(0, 0, 100, 100), 1.0)
    animator = make_animator([zoomed_out, zoomed_in])
    animation = RecordingAnimation()
    animator.register(StubLink(), animation)

    animator.tick(1000)

    assert animation.times == [1.0]


# ======== Pulse ========= #


def test_pulse_moves_at_its_speed():
    pulse = PulseAnimation()
    assert pulse.offset is None

    pulse.advance(1.5)

    assert pulse.offset == pytest.approx(1.5 * pulse.speed)

    pulse.reset()
    assert pulse.offset is None


# ======== Styles ========= #


def test_every_style_has_an_animation():
    from nyx.editor.graphics.animation.styles import ANIMATION_CLASSES
    from nyx.static.enums import LinkAnimationStyle

    assert set(ANIMATION_CLASSES) == set(LinkAnimationStyle)


def test_create_animation_makes_the_animation_of_the_style():
    from nyx.editor.graphics.animation.styles import create_animation
    from nyx.static.enums import LinkAnimationStyle

    animation = create_animation(LinkAnimationStyle.PULSE)

    assert isinstance(animation, PulseAnimation)
    assert create_animation(LinkAnimationStyle.PULSE) is not animation
