from cognite_toolkit._cdf_tk.validation.warning import ToolkitWarning, WarningList


class ToolkitCommand:
    def __init__(self, print_warning: bool = True):
        self.print_warning = print_warning
        self.warning_list = WarningList[ToolkitWarning]()

    def warn(self, warning: ToolkitWarning) -> None:
        self.warning_list.append(warning)
        if self.print_warning:
            print(warning)