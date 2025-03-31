# Graphics
from src.canvas import Canvas
from src.menu import Menu
from src.menu_element import MenuElement, Spacing, Title, InputField, Text
from src.gui_element import GUIElement
# Functionality
from src.worker import worker
from src.api_handler import CursesError
# Library
import asyncio
import curses
import datetime 


# This file contains the main loop for the curses GUI. It is responsible for rendering the GUI and handling input.
# The GUI is composed of a banner, a menu, and a GUI element. The menu is a list of MenuElements, which can be selected with the arrow keys.
# The GUI element is a list of strings, which can be used to display information to the user.




# TODO:
# Probably also want to display the total time elapsed for the job
# Maybe also have the iterations per second




banner = [
    "   ___                _              _  _ _         ",
    "  / _ \\ _  _ __ _ _ _| |_ _  _ _ __ | || (_)_ _____ ",
    " | (_) | || / _` | ' \\  _| || | '  \\| __ | \\ V / -_)",
    "  \\__\\_\\\\_,_\\__,_|_||_\\__|\\_,_|_|_|_|_||_|_|\\_/\\___|"
]


options = {
    "center_menu": True
}



# One time initialization of the banner and the menus
banner_canvas = Canvas(max_width=60, max_height=6)
banner_canvas.from_list(banner)
banner_canvas.add_border(extend=True)

show_menu = False
def toggle_menu():
    global show_menu
    show_menu = not show_menu

def menu_show():
    global show_menu
    show_menu = True
######################################
#           MENU SECTION             #
######################################
# Define the menus
logged_out_menu = Menu()
logged_in_menu_not_running = Menu()
logged_in_menu_running = Menu()
settings_menu = Menu()
quit_confirm = Menu()
login_menu = Menu()
wrong_credentials_popup = Menu()
login_success_popup = Menu()
logout_success_popup = Menu()
worker_started_popup = Menu()
worker_stopped_popup = Menu()
# Set the initial menu
menu = logged_out_menu
current_menu = menu

# Define the named menu elements and actions
menu_title = Title("Menu")
login_btn = MenuElement("Log in", links=login_menu)
def logout_action():
    global menu
    menu = logged_out_menu
    worker.api_handler.access_token = ""
    worker.api_handler.refresh_token = ""
    worker.username = None
    worker.logged_in = False
async def login_action():
    global menu
    if await worker.login(username_field.input, password_field.input):
        menu = logged_in_menu_running if worker.running else logged_in_menu_not_running
        login_button.links = login_success_popup
    else:
        login_button.links = wrong_credentials_popup
logout_btn = MenuElement("Log out", action=logout_action, links=logout_success_popup)
settings_btn = MenuElement("Settings", links=settings_menu)
hide_menu_btn = MenuElement("Hide menu", action=toggle_menu)
quit_btn = MenuElement("Quit", links=quit_confirm)
username_field = InputField("Username")
password_field = InputField("Password", hidden=True)
login_button = MenuElement("Login", action=login_action)
start_worker_btn = MenuElement("Start worker", action=worker.start, links=worker_started_popup)
stop_worker_btn = MenuElement("Stop worker", action=worker.stop, links=worker_stopped_popup)


# Compose the menus
# logged_in_menu when worker is not running
logged_in_menu_not_running.add_element(menu_title)
logged_in_menu_not_running.add_element(Spacing())
logged_in_menu_not_running.add_element(start_worker_btn)
logged_in_menu_not_running.add_element(logout_btn)
logged_in_menu_not_running.add_element(settings_btn)
logged_in_menu_not_running.add_element(Spacing())
logged_in_menu_not_running.add_element(hide_menu_btn)
logged_in_menu_not_running.add_element(Spacing())
logged_in_menu_not_running.add_element(quit_btn)
# logged_in_menu when worker is running
logged_in_menu_running.add_element(menu_title)
logged_in_menu_running.add_element(Spacing())
logged_in_menu_running.add_element(stop_worker_btn)
logged_in_menu_running.add_element(logout_btn)
logged_in_menu_running.add_element(settings_btn)
logged_in_menu_running.add_element(Spacing())
logged_in_menu_running.add_element(hide_menu_btn)
logged_in_menu_running.add_element(Spacing())
logged_in_menu_running.add_element(quit_btn)
# logged_out_menu
logged_out_menu.add_element(menu_title)
logged_out_menu.add_element(Spacing())
logged_out_menu.add_element(login_btn)
logged_out_menu.add_element(Spacing())
logged_out_menu.add_element(hide_menu_btn)
logged_out_menu.add_element(Spacing())
logged_out_menu.add_element(quit_btn)
# menu (which one to show)
menu = logged_out_menu
# submenu
settings_menu.add_element(Title("This is a submenu."))
settings_menu.add_element(Spacing())
settings_menu.add_element(MenuElement("Suboption 1, this is very very long and will be the longest of all!", action =lambda: print("Suboption 1 selected")))
settings_menu.add_element(MenuElement("Back", links=lambda: menu))
# quit confirmation
quit_confirm.add_element(Title("Are you sure you want to quit?"))
quit_confirm.add_element(Spacing())
quit_confirm.add_element(MenuElement("No", links = lambda: menu))
def quit_action():
    raise KeyboardInterrupt()
quit_confirm.add_element(MenuElement("Yes", action=quit_action))
# login menu
login_menu.add_element(Title("Insert your credentials to log in"))
login_menu.add_element(Spacing())
login_menu.add_element(username_field)
login_menu.add_element(password_field)
login_menu.add_element(Spacing())
login_menu.add_element(login_button)
login_menu.add_element(MenuElement("Back", links=lambda: menu))
# wrong credentials popup
wrong_credentials_popup.add_element(Title("Wrong credentials!"))
wrong_credentials_popup.add_element(Spacing())
wrong_credentials_popup.add_element(MenuElement("Ok", links=login_menu))
# login success popup
login_success_popup.add_element(Title("Login successful!")) 
login_success_popup.add_element(Spacing())
login_success_popup.add_element(MenuElement("Ok", links= lambda: menu))
# logout success popup
logout_success_popup.add_element(Title("Logout successful!"))
logout_success_popup.add_element(Spacing())
logout_success_popup.add_element(MenuElement("Ok", links= lambda: menu))
# worker started popup
worker_started_popup.add_element(Title("Worker started!"))
worker_started_popup.add_element(Spacing())
worker_started_popup.add_element(MenuElement("Ok", links= lambda: menu))
# worker stopped popup
worker_stopped_popup.add_element(Title("Worker stopped!"))
worker_stopped_popup.add_element(Spacing())
worker_stopped_popup.add_element(MenuElement("Ok", links= lambda: menu))
# error popup
error_popup = Menu()
error_popup.add_element(Title("An error occurred!"))
error_popup.add_element(Spacing())
error_popup.add_element(Title("%error%"))
error_popup.add_element(MenuElement("Ok", links= lambda: menu, action=lambda: toggle_menu()))



######################################
#           GUI SECTION              #
######################################
welcome_message_gui = GUIElement(max_width=100, max_heigh=100)
welcome_message_gui.add_text('''Welcome to the QuantumHive terminal interface!
                            
QuantumHive is used to find a numerical estimate for the minimal output entropy (MOE) of quantum channels.

You are currently running the QuantumHive worker. Thank you! You will help complete jobs, which are managed by a central server. This way, large computations can be broken down into more manageable chunks.

Please ensure you are logged in. If you are unsure if you have a user, please get in touch with the creator. If you need a job completed, also get in touch.

Happy computing!''')

# Welcome message (logged in)
welcome_gui = GUIElement(max_width=100, max_heigh=100)
welcome_gui.add_element(Title(f"Welcome, %user%!"))
welcome_gui.add_element(Spacing())
welcome_gui.add_element(Title(f"You are currently %login_status%."))

# Stats GUI
stats_gui = GUIElement(max_width=100, max_heigh=100)
stats_gui.add_element(Title("Worker status"))
stats_gui.add_element(Spacing())
stats_gui.add_element(Title(f"Worker is %running_status%."))
stats_gui.add_element(Title(f"Current task: %current_task%."))
stats_gui.add_element(Spacing())
stats_gui.add_element(Title(f"Last server update: %last_update%."))

# Job GUI
job_gui = GUIElement(max_width=100, max_heigh=100)
job_gui.add_element(Title("Job status"))
job_gui.add_element(Spacing())
job_gui.add_element(Title(f"Job is %job_status%."))
job_gui.add_element(Title(f"Current task: %current_task%."))
job_gui.add_element(Spacing())
job_gui.add_element(Title(f"Current entropy: %entropy%."))
job_gui.add_element(Title(f"Current iteration: %iteration%."))


# Command GUI
command_gui = GUIElement(max_width=100, max_heigh=100)
command_gui.add_element(Title("Last worker updates"))
command_gui.add_element(Spacing())
command_gui.add_element(Title(f"%update1%"))
command_gui.add_element(Title(f"%update2%"))
command_gui.add_element(Title(f"%update3%"))

# api handler gui
api_handler_gui = GUIElement(max_width=100, max_heigh=100)




######################################
#           MAIN LOOP                #
######################################
async def update_screen(stdscr):
    """Main curses UI loop with async updates"""

    global menu, logged_in_menu_not_running, logged_in_menu_running, logged_out_menu, current_menu, welcome_gui, stats_gui

    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(1)  # Non-blocking input
    stdscr.timeout(50)  # Refresh every 50ms (20fps, decent for a terminal)


    # Start by initializing the screen
    height, width = stdscr.getmaxyx()
    screen = Canvas(max_width=width-1, max_height=height-1)
    screen.width = width
    screen.height = height
    for _ in range(height):
        screen.add_line(" "*width)
    screen.resize()



    while True:
        try:
            # Get terminal size
            height, width = stdscr.getmaxyx() # These are indexed starting from 1! Reduce them by one or risk overflow
            height -= 1
            width -= 1

            # Check resize
            resized = (height != screen.max_height) or (width != screen.max_width)

            # Check if the terminal is too small
            if height < 10 or width < 60:
                stdscr.clear()
                stdscr.addstr(0, 0, "Terminal too small! Please resize.")
                stdscr.refresh()
                await asyncio.sleep(0.5)
                continue

            # If terminal has been resized, create a new screen
            if resized:
                screen = Canvas(max_width=width, max_height=height)
                screen.resize()
                # reset number of lines
                screen.from_list([" "*width for _ in range(height)])

            for i in range(height):
                screen.write_line(" "*width, 0 , i)

            # Print banner at the top
            screen.replace(banner_canvas, 1, 1)

            # Print help screen at the bottom
            if not show_menu:
                help_canvas = Canvas(max_width=width, max_height=height)
                help_canvas.add_line("Press 'm' to toggle menu, 'q' to quit")
                screen.replace(help_canvas, 1, height-2)        
            
            # select the current gui and menus depending on login status
            if await worker.is_logged_in():
                if worker.running:
                    menu = logged_in_menu_running
                else:
                    menu = logged_in_menu_not_running

                # get username right
                welcome_gui.reset_texts()
                welcome_gui.replace_text_occurences(f"%user%", worker.username)
                welcome_gui.replace_text_occurences(f"%login_status%", "logged in")

                stats_gui.reset_texts()
                stats_gui.replace_text_occurences(f"%running_status%", "running" if worker.running else "not running")
                stats_gui.replace_text_occurences(f"%current_task%", worker.job_type if worker.has_job else "none")
                stats_gui.replace_text_occurences(f"%last_update%", f"{(datetime.datetime.now()-worker.last_checked).seconds} s")

                job_gui.reset_texts()
                job_gui.replace_text_occurences(f"%job_status%", "running" if worker.has_job else "not running")
                job_gui.replace_text_occurences(f"%current_task%", worker.job_type if worker.has_job and worker.job_type else "none")
                job_gui.replace_text_occurences(f"%entropy%", str(worker.current_entropy) if worker.has_job else "n/a")
                job_gui.replace_text_occurences(f"%iteration%", str(worker.current_iterations) if worker.has_job and worker.current_iterations else "n/a")





                # Get a snapshot of last commands without consuming them
                queue_snapshot = await worker.last_commands.get_all()

                # Replace placeholders in GUI
                command_gui.reset_texts()
                command_gui.replace_text_occurences(f"%update3%", queue_snapshot[-1] if len(queue_snapshot) > 0 else "n/a")
                command_gui.replace_text_occurences(f"%update2%", queue_snapshot[-2] if len(queue_snapshot) > 1 else "n/a")
                command_gui.replace_text_occurences(f"%update1%", queue_snapshot[-3] if len(queue_snapshot) > 2 else "n/a")
            else:
                welcome_gui.reset_texts()
                welcome_gui.replace_text_occurences(f"%user%", "stranger")
                welcome_gui.replace_text_occurences(f"%login_status%", "not logged in")

                stats_gui.reset_texts()
                stats_gui.replace_text_occurences(f"%running_status%", "not running")
                stats_gui.replace_text_occurences(f"%current_task%", "none")
                stats_gui.replace_text_occurences(f"%last_update%", "n/a")

                job_gui.reset_texts()
                job_gui.replace_text_occurences(f"%job_status%", "not running")
                job_gui.replace_text_occurences(f"%current_task%", "none")
                job_gui.replace_text_occurences(f"%entropy%", "n/a")
                job_gui.replace_text_occurences(f"%iteration%", "n/a")


                menu = logged_out_menu

            welcome_gui_canvas = welcome_gui.to_canvas(border=False)
            screen.replace(welcome_gui_canvas, 1, 20)
            
            stats_gui_canvas = stats_gui.to_canvas(border=True)
            screen.replace(stats_gui_canvas, 1, 13)

            job_gui_canvas = job_gui.to_canvas(border=True)
            l = stats_gui_canvas.width + 2
            screen.replace(job_gui_canvas, l, 13)

            command_gui_canvas = command_gui.to_canvas(border=True)
            ll = stats_gui_canvas.width + job_gui_canvas.width + 3
            screen.replace(command_gui_canvas, ll, 13)
            
            api_handler_gui.reset_texts()
            api_handler_gui.replace_text_occurences(f"%text%", worker.api_handler.status)

            api_handler_gui.elements = []
            api_handler_gui.add_element(Title("API Handler status"))
            api_handler_gui.add_element(Spacing())

            api_handler_gui.add_text(worker.api_handler.status, border=True)




            api_handler_gui_canvas = api_handler_gui.to_canvas(border=True)
            lll = stats_gui_canvas.width + job_gui_canvas.width + command_gui_canvas.width + 4
            screen.replace(api_handler_gui_canvas, lll, 13)
            

            very_long_text_gui_canvas = welcome_message_gui.to_canvas(border=False)
            #screen.replace(very_long_text_gui_canvas, 1, 8)


            # Add the menu. this should be done last, since menu is always on top.
            if show_menu:
                menu_canvas = current_menu.to_canvas(True)

                xoffset = (screen.width-menu_canvas.width)//2 if options["center_menu"] else 5
                yoffset = (screen.height-menu_canvas.height)//2 if options["center_menu"] else 5
                screen.replace(menu_canvas, xoffset, yoffset)
        
            # Handle input for menu
            key = await asyncio.to_thread(stdscr.getch)  # Non-blocking input

            try:
                if not show_menu:
                    if key == ord("m"):
                        toggle_menu()
                    elif key == ord("q"):
                        raise KeyboardInterrupt()
                if show_menu:
                    current_menu = await current_menu.handle_input(key)
            except KeyboardInterrupt:
                # Exit the program
                # Await the worker to finish
                # TODO : implement
                if worker.task:
                    worker.stop()
                    await worker.task
                return
        # Clear screen
            stdscr.clear()

            # Add lines from Screen to curses
            for i, line in enumerate(screen.to_list()):
                    stdscr.addstr(i, 0, line[:width])


            stdscr.refresh()



            await asyncio.sleep(0.05)  # Non-blocking sleep
        except curses.error:
            pass

        except CursesError as e:
            # Add a popup for the error
            error_popup.reset_texts()
            error_popup.replace_text_occurences(f"%error%", e.message)
            current_menu = error_popup
            menu_show()

            continue


