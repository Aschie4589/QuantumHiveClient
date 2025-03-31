from src.canvas import Canvas
import curses 
class Menu:
    def __init__(self, parent=None): # arbitrary default values
        self.elements = [] # Lists: option, action/submenu
        self.selected = -1
        self.parent = parent

        self.hpadding = 4
        self.vpadding = 2
        self.center_menu = True

    def get_first_selectable(self):
        for i, option in enumerate(self.elements):
            if option.selectable:
                return i
        return -1

    def reset_cursor(self):
        # deselect all elements
        for option in self.elements:
            option.deselect()
        # select the first selectable element
        self.selected = self.get_first_selectable()
        if self.selected >= 0:
            self.elements[self.selected].select()

    def add_element(self, option):
        self.elements.append(option)
        self.selected = self.get_first_selectable()
        if self.selected >= 0:
            self.elements[self.selected].select()

    def move_up(self):
        # get the previous selectable element
        current = self.selected
        while self.selected > 0:
            self.selected -= 1
            if self.elements[self.selected].selectable:
                break
        if not self.elements[self.selected].selectable:
            self.selected = current
        # deselect the last element and select the new one
        self.elements[current].deselect()
        self.elements[self.selected].select()

    def move_down(self):
        # get the next selectable element
        current = self.selected
        while self.selected < len(self.elements)-1:
            self.selected += 1
            if self.elements[self.selected].selectable:
                break
        if not self.elements[self.selected].selectable:
            self.selected = current
        # deselect the last element and select the new one
        self.elements[current].deselect()
        self.elements[self.selected].select()
        

    async def handle_input(self, key):
        if key == curses.KEY_UP:
            self.move_up()
        elif key == curses.KEY_DOWN:
            self.move_down()
        # escape key
        elif (key == 27 or key == 127) and self.parent:  # Escape key to go back (if submenu)
            self.parent.reset_cursor()
            return self.parent

        # other key presses are passed to the selected element
        else:
            r = await self.elements[self.selected].handle_input(key)
            if r:
                return r
        return self  # Stay in the same menu

    def to_canvas(self, border=True):
        canvas = Canvas(max_width=1000, max_height=1000) # very bad practice. TODO: fix this
        # obtain strings from all elements
        strings  = [str(option) for option in self.elements]

        # calculate width of the menu and canvas size
        max_text_width = max([len(s) for s in strings])
        canvas.width = max_text_width + 2*self.hpadding
        canvas.height = len(self.elements) + 2*self.vpadding
        # note: canvas might be larger than the screen. If printing to screen, make sure to superimpose this menu onto a correctly sized screen.        

        # calculate width of the selectable elements, and center them if needed
        selectable_width = max([len(s) for (i,s) in enumerate(strings) if self.elements[i].selectable])
        
        # add padding blank lines
        for _ in range(canvas.height):
            canvas.add_line(" "*canvas.width)

        # add elements
        for i, el in enumerate(strings):            
            l = (canvas.width - selectable_width)//2 if self.center_menu and self.elements[i].selectable else self.hpadding
            canvas.write_line(el, l, i+self.vpadding)    

        if border:
            canvas.add_border(True) # Extends the canvas
        return canvas


def exit_program():
    """A function that raises an exception to exit curses"""
    raise KeyboardInterrupt  # This will break out of curses safely