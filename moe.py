import curses
import asyncio
# curses gui elements
from src.gui import *


def main():
    """Manages curses and background task cleanly"""
    loop = asyncio.new_event_loop()
    curses.wrapper(lambda stdscr: loop.run_until_complete(update_screen(stdscr)))
    # Start the background worker task



# Main entry point
if __name__ == "__main__":
    main()



