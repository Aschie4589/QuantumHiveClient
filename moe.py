import curses
import asyncio
# graphics
from src.canvas import Canvas
from src.menu import Menu
from src.menu_element import MenuElement, Spacing, Title, InputField
from src.gui_element import GUIElement
# functionality
from src.worker import worker
# curses gui elements
from src.gui import *



def run_curses():
    """Run curses with asyncio support"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    curses.wrapper(lambda stdscr: loop.run_until_complete(update_screen(stdscr)))


def main():
    """Manages curses and background task cleanly"""
    loop = asyncio.new_event_loop()
    curses.wrapper(lambda stdscr: loop.run_until_complete(update_screen(stdscr)))
    # Start the background worker task



# Main entry point
if __name__ == "__main__":
    main()



