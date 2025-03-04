import curses

class MenuElement:
    def __init__(self, text, action=None, links=None):
        self.template_text = text
        self.text = text
        self.action = action
        self.links = links
        self.selectable = True
        self.selected = False

    def handle_input(self, key):
        # Returns the action if it is not callable = it is a submenu
        # Returns None if the action is callable
        # Enter key
        if key in (curses.KEY_ENTER, 10, 13):
            return self.execute()
        return None

    def __str__(self):
        return " "+ self.text+ " " if not self.selected else f"[{self.text}]"

    def __repr__(self):
        return self.text

    def select(self):
        self.selected = True

    def deselect(self):
        self.selected = False

    def execute(self):
        # if it is callable, call it
        if callable(self.action):
            self.action()

        if self.links:
            # this should be updated dynamically. I.e. sometimes links will be a lambda; in that case the lambda returns the submenu
            if callable(self.links):
                self.links().reset_cursor()
                return self.links()
            self.links.reset_cursor()
            return self.links
        return None    

    def replace(self, old_string, new_string):
        # replace old_string with new_string, using self.template_text as the base
        self.text = self.text.replace(old_string, new_string)

    def reset_text(self):
        self.text = self.template_text

class Spacing(MenuElement):
    def __init__(self):
        self.template_text = ""
        self.text = ""
        self.selectable = False

    def handle_input(self, key):
        return None

    def __str__(self):
        return ""

    def __repr__(self):
        return ""

    def execute(self):
        pass

class Title(MenuElement):
    def __init__(self, text):
        self.text = text
        self.template_text = text
        self.selectable = False

    def handle_input(self, key):
        return None

    def __str__(self):
        return self.text

    def __repr__(self):
        return self.text

    def execute(self):
        pass

class InputField(MenuElement):
    def __init__(self, text, hidden=False, shown_input_characters=10):
        self.text = text
        self.template_text = text
        self.action = False
        self.selectable = True
        self.selected = False
        self.hidden = hidden
        self.input = ""
        self.shown_input_characters = shown_input_characters

    def handle_input(self, key):
        if key == 127:  # Backspace
            self.input = self.input[:-1]
        elif key == curses.KEY_DC:  # Delete
            self.input = ""
        elif key >= 32 and key <= 126:
            self.input += chr(key)
        return None

    def __str__(self):
        # if the input is longer than the shown characters, only show the last characters. Otherwise, pad with spaces after cursor
        cursor_symbol = "_" if self.selected else " "
        # handle the cases where the input is too short, and too long
        if not self.hidden:
            if len(self.input) < self.shown_input_characters:
                strg = f"{self.input}{cursor_symbol}{' '*(self.shown_input_characters-len(self.input))}"
            else:
                strg = f"{self.input[-self.shown_input_characters:]}{cursor_symbol}"
        else:
            if len(self.input) < self.shown_input_characters:
                strg = f"{'*'*len(self.input)}{cursor_symbol}{' '*(self.shown_input_characters-len(self.input))}"
            else:
                strg = f"{'*'*self.shown_input_characters}{cursor_symbol}"
        return f" {self.text}: [{strg}]"

    def __repr__(self):
        return self.text

    def execute(self):
        pass

