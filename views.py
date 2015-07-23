
import sublime
import utils

####################################################################################
#   VIEW
####################################################################################

class SwiDebugView(object):
    """ The SWIDebugView is sort of a normal view with some convenience methods.
        See lookup_view.
    """
    def __init__(self, v):
        self.view = v
        self.context_data = {}
        self.clicks = []
        self.prev_click_position = 0

    def __getattr__(self, attr):
        if hasattr(self.view, attr):
            return getattr(self.view, attr)
        if attr.startswith('on_'):
            return self
        raise AttributeError

    def __call__(self, *args, **kwargs):
        pass

    def window(self):
        return self.view.window()

    def uri(self):
        return 'file://' + os.path.realpath(self.view.file_name())

    def lines(self, data=None):
        """ Takes a list of line numbers, regions, or else uses the selection.
            Returns regions, each covering one complete line, 
            representing the lines included in the supplied input.
        """ 
        lines = []
        if data is None:
            regions = self.view.sel()
        else:
            if type(data) != list:
                data = [data]
            regions = []
            for item in data:
                if type(item) == int or item.isdigit():
                    regions.append(self.view.line(self.view.text_point(int(item) - 1, 0)))
                else:
                    regions.append(item)

        for i in range(len(regions)):
            lines.extend(self.view.split_by_newlines(regions[i]))
        return [self.view.line(line) for line in lines]

    def rows(self, lines):
        """ Takes one or more lines and returns the 1-based (?)
            line and column of the first character in the line.
        """
        if not type(lines) == list:
            lines = [lines]
        return [self.view.rowcol(line.begin())[0] + 1 for line in lines]

    def insert_click(self, a, b, click_type, data):
        """ Creates a clickable "button" at the specified line and column.
            Records the action to be taken on click, and any parameter
            such as the object to get members from.
        """
        insert_before = 0
        new_region = sublime.Region(a, b)
        regions = self.view.get_regions('swi_log_clicks')
        for region in regions:
            if new_region.b < region.a:
                break
            insert_before += 1

        self.clicks.insert(insert_before, {'click_type': click_type, 'data': data})

        regions.append(new_region)
        self.view.add_regions('swi_log_clicks', regions, scope=utils.get_setting('interactive_scope'), flags=sublime.DRAW_NO_FILL)

    def print_click(self, edit, position, text, click_type, data):
        """ Inserts the specified text and creates a clickable "button"
            around it.
        """
        insert_length = self.insert(edit, position, text)
        self.insert_click(position, position + insert_length, click_type, data)

    def remove_click(self, index):
        """ Removes a clickable "button" with the specified index."""
        regions = self.view.get_regions('swi_log_clicks')
        del regions[index]
        self.view.add_regions('swi_log_clicks', regions, scope=utils.get_setting('interactive_scope'), flags=sublime.DRAW_NO_FILL)

    def clear_clicks(self):
        """ Removes all clickable regions """
        self.clicks = []

    def check_click(self):
        if not isinstance(self, SwiDebugView):
            return

        cursor = self.sel()[0].a

        click_counter = 0
        click_regions = self.get_regions('swi_log_clicks')
        for click in click_regions:
            if cursor > click.a and cursor < click.b:

                if click_counter < len(self.clicks):
                    click = self.clicks[click_counter]

                    if click['click_type'] == 'goto_file_line':
                        open_script_and_focus_line(click['data']['scriptId'], click['data']['line'])

                    if click['click_type'] == 'goto_call_frame':
                        callFrame = click['data']['callFrame']
                        change_to_call_frame(callFrame)

                    if click['click_type'] == 'get_params':
                        if channel:
                            channel.send(webkit.Runtime.getProperties(click['data']['objectId'], True), console_add_properties, click['data'])

                    if click['click_type'] == 'command':
                        self.remove_click(click_counter)
                        self.window().run_command(click['data'])

            click_counter += 1

def find_view(console_type, title=''):
    found = False
    v = None
    window = sublime.active_window()

    if console_type.startswith('console'):
        group = 1
        fullName = "Javascript Console"

    if console_type == 'stack':
        group = 2
        fullName = "Javascript Callstack"

    if console_type.startswith('scope'):
        group = 1
        fullName = "Javascript Scope"

    if console_type.startswith('mapping'):
        group = 0
        fullName = "File mapping"

    if console_type.startswith('styles'):
        group = 1
        fullName = "Styles"

    window.focus_group(group)
    fullName = fullName + ' ' + title

    for v in window.views():
        if v.name() == fullName:
            found = True
            break

    if not found:
        v = window.new_file()
        v.set_scratch(True)
        v.set_read_only(False)
        v.set_name(fullName)
        v.settings().set('word_wrap', False)

    window.set_view_index(v, group, 0)

    if console_type.startswith('console'):
        v.set_syntax_file('Packages/Web Inspector/swi_log.tmLanguage')

    if console_type == 'stack':
        v.set_syntax_file('Packages/Web Inspector/swi_stack.tmLanguage')

    if console_type.startswith('scope'):
        v.set_syntax_file('Packages/Web Inspector/swi_log.tmLanguage')

    window.focus_view(v)

    v.set_read_only(False)

    return lookup_view(v)

buffers  = {}

def lookup_view(v):
    '''
    Convert a Sublime View into an SWIDebugView
    '''
    if isinstance(v, SwiDebugView):
        return v
    if isinstance(v, sublime.View):
        id = v.buffer_id()
        if id in buffers:
            buffers[id].view = v
        else:
            buffers[id] = SwiDebugView(v)
        return buffers[id]
    return None