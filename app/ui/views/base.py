class ViewBase:

    """Shared base for extracted MainWindow views.

    A view renders into a parent frame and reaches shared window state and
    helpers through ``self.win`` (the MainWindow instance). Views own their
    local widgets only; shared widgets/state stay on MainWindow so the rest
    of the application (shortcuts, set_view, voice commands) keeps working.
    """

    def __init__(self, win):
        self.win = win
