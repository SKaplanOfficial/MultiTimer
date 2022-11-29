import PyXA
from typing import Any, Callable, Union
from datetime import datetime, timedelta
from threading import Timer

active_timers = []  #: List of currently active timers
timer_submenus = [] #: List of timer-specific submenu items

menu_bar = PyXA.XAMenuBar() #: Global menubar object

timer_icon = PyXA.XAImage.symbol("timer") #: Icon displayed in the menubar
timer_menu = menu_bar.new_menu(image=timer_icon, image_dimensions=(100, 100)) #: Menu that appears when icon is clicked
status_indicator = timer_menu.new_item("No active timers") #: Active timer list (submenus attached in start_timer)

class SimpleTimer:
    """State management class for pauseable/resumable timers.
    """
    def __init__(self, title: str, duration: float, action: Union[Callable[[], None], None] = None, args: Union[list[Any], None] = None):
        self.title = title #: Name of the timer, e.g. "10 minutes"
        self.duration = duration #: Numeric duration of the timer in seconds
        self.started = False #: Whether the timer has been started
        self.paused = False #: Whether the timer is currently paused
        self.finished = False #: Whether the timer is complete
        self.action = action #: The method to call when the timer completes
        self.args = args or [] #: The arguments to pass to the action method
        self.creation_time = datetime.now() #: The date and time that the timer was created
        self.end_time = datetime.now() + timedelta(seconds=duration) #: The date and time that the timer is expected to end. Updates when timer is paused/resumed
        self.__timer = Timer(duration, self.run_action)

    @property
    def time_remaining(self) -> timedelta:
        """The time in seconds until the timer is complete, adjusted according to pause/resume state.
        """
        if self.finished:
            return timedelta(seconds=0)
        elif self.paused:
            return self.__time_remaining
        else:
            return self.end_time - datetime.now()

    def start(self):
        """Starts the timer.
        """
        self.started = True
        self.__timer.start()

    def cancel(self):
        """Immediately ends the timer, with no option to resume it later on.
        """
        self.__timer.cancel()

    def pause(self):
        """Pauses the timer, allowing it to be resumed later on.
        """
        self.__time_remaining = self.time_remaining
        self.paused = True
        self.__timer.cancel()

    def resume(self):
        """Resumes the timer from a paused state.
        """
        self.end_time = datetime.now() + self.time_remaining
        self.__timer = Timer(self.time_remaining.total_seconds(), self.run_action)
        self.__timer.start()
        self.paused = False

    def run_action(self):
        """Runs the timer's associated action method.
        """
        self.finished = True
        self.action(self, *self.args)

def show_alert(timer: SimpleTimer):
    """Shows an alert that a timer has completed.
    """
    submenu = timer_submenus.pop(active_timers.index(timer))
    submenu.delete()

    active_timers.remove(timer)
    update_status_indicator()
    PyXA.XAAlert(title=f"Your timer for {timer.title} has ended!", message="Timer Complete", icon=PyXA.XAImage.symbol("clock.badge.checkmark")).display()

def update_status_indicator():
    """Updates the active timers status indicator to reflect the amount of currently active timers.
    """
    num_timers = len(active_timers)
    if num_timers == 0:
        status_indicator.title = "No active timers"
        status_indicator.enabled = False
    elif num_timers == 1:
        status_indicator.title = f"1 active timer" 
    else:
        status_indicator.title = f"{num_timers} active timers"

def cancel_timer(item, button, timer):
    """Cancels a timer and removes it from the active timer list.
    """
    submenu = timer_submenus.pop(active_timers.index(timer))
    submenu.delete()

    timer.cancel()
    active_timers.remove(timer)
    update_status_indicator()

def resume_timer(item, button, timer):
    """Resumes a timer and updates its submenu actions.
    """
    timer.resume()
    item.title = "Pause"
    item.action = pause_timer

def pause_timer(item, button, timer):
    """Pauses a timer and updates its submenu actions.
    """
    timer.pause()

    hours, remainder = divmod(timer.time_remaining.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    time_str = f"{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
    if hours > 0:
        time_str = f"{str(int(hours)).zfill(2)}:" + time_str

    item.title = "Resume"
    item.action = resume_timer

def update_submenus(menu, button):
    """Updates a timer's submenu to reflect its time remaining.
    """
    for index, timer in enumerate(active_timers):
        submenu = timer_submenus[index]
        hours, remainder = divmod(timer.time_remaining.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{str(int(minutes)).zfill(2)}:{str(int(seconds)).zfill(2)}"
        if hours > 0:
            time_str = f"{str(int(hours)).zfill(2)}:" + time_str

        if timer.paused:
            time_str = "Paused, " + time_str

        submenu.title = submenu.title[0:submenu.title.index("(") + 1] + f"{time_str} remaining)"

def start_timer(item, button, duration: float):
    """Starts a new timer, creates new submenu for it, and adds the timer to the active timers list.
    """
    title = item.title
    if title == "Custom Timer...":
        if duration < 60:
            title = f"{duration} seconds"
        else:
            title = f"{round(duration / 60.0, 2)} minutes"
    timer = SimpleTimer(title, duration, show_alert)

    active_timers.append(timer)
    status_indicator.enabled = True
    update_status_indicator()

    hours, remainder = divmod(timer.time_remaining.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    time_str = f"{int(minutes)}:{int(seconds)}"
    if hours > 0:
        time_str = f"{int(hours)}:" + time_str

    timer_submenu = status_indicator.new_subitem(f"{title} ({time_str} remaining)")
    timer_submenu.new_subitem("Pause", action=pause_timer, args=[timer])
    timer_submenu.new_subitem("Cancel", action=cancel_timer, args=[timer])
    timer_submenus.append(timer_submenu)
    timer.start()

def create_custom_timer(item, button):
    """Prompts user for custom duration input and creates a timer with the that duration.
    """
    response = PyXA.XADialog("Custom timer duration (minutes):", default_answer="5").display()
    if (response):
        duration = float(response[1])
        start_timer(item, button, duration * 60.0)

if __name__ == "__main__":
    # When the status indicator is hovered over, update all timer submenus
    status_indicator.action = update_submenus

    # Grey-out the status indicator until a timer is created
    status_indicator.enabled = False

    # Construct and display menu
    timer_menu.add_separator()
    timer_menu.new_item("1 minute", action=start_timer, args=[60.0])
    timer_menu.new_item("5 minutes", action=start_timer, args=[300.0])
    timer_menu.new_item("10 minutes", action=start_timer, args=[600.0])
    timer_menu.new_item("30 minutes", action=start_timer, args=[1800.0])
    timer_menu.new_item("1 hour", action=start_timer, args=[3600.0])
    timer_menu.new_item("Custom Timer...", action=create_custom_timer)
    timer_menu.add_separator()
    menu_bar.display()