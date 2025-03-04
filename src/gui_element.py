from src.canvas import Canvas
import curses 
class GUIElement:
    def __init__(self, max_width=1000, max_heigh=1000): # arbitrary default values
        self.elements = [] # Lists: option, action/submenu

        self.max_width = max_width
        self.max_height = max_heigh

        self.hpadding = 1
        self.vpadding = 0



    def add_element(self, option):
        self.elements.append(option)


    def to_canvas(self, border=True):
        canvas = Canvas(max_width=self.max_width, max_height=self.max_height)
        # obtain strings from all elements
        strings  = [str(option) for option in self.elements]

        # calculate width of the menu and canvas size
        max_text_width = max([len(s) for s in strings])

        canvas.width = min(max_text_width + 2*self.hpadding, self.max_width)
        canvas.height = min(len(self.elements) + 2*self.vpadding, self.max_height)
        
        # add blank lines
        for _ in range(canvas.height):
            canvas.add_line(" "*canvas.width)

        # add elements
        for i, el in enumerate(strings):            
            l = self.hpadding
            canvas.write_line(el, l, i+self.vpadding)    

        if border:
            canvas.add_border(True) # Extends the canvas

        return canvas


    def replace_text_occurences(self, old_text, new_text):
        for el in self.elements:
            el.replace(old_text, new_text)

    def reset_texts(self):
        for el in self.elements:
            el.reset_text()