from nyx.api.v1 import Stage


def test_opened_stages_get_the_configured_undo_limit(
    main_window, stage_editor, restore_config
):
    behaviour = restore_config(main_window.config.values.editor_behaviour, "undo_limit")
    behaviour.undo_limit = 7

    stage_editor.set_stage(Stage())

    assert stage_editor.stage.undo_limit == 7


def test_new_stages_get_the_default_limit(stage_editor):
    assert (
        stage_editor.stage.undo_limit
        == stage_editor.main_window.config.values.editor_behaviour.undo_limit
    )
