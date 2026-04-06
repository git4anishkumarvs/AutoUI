from behave import when, use_step_matcher

# Switch to Regular Expression matcher to support optional groups cleanly!
use_step_matcher("re")

@when('I click on "(?P<locator>[^"]+)"(?: identified by "(?P<locator_type>[^"]+)")? in "(?P<app_alias>[^"]+)"')
def step_click(context, locator, app_alias, locator_type=None):
    if locator_type is None:
        locator_type = "default"
    context.app_manager.interact_click(app_alias, locator, locator_type)

@when('I type "(?P<text>[^"]+)" into "(?P<locator>[^"]+)"(?: identified by "(?P<locator_type>[^"]+)")? in "(?P<app_alias>[^"]+)"')
def step_type(context, text, locator, app_alias, locator_type=None):
    if locator_type is None:
        locator_type = "default"
    context.app_manager.interact_type(app_alias, locator, text, locator_type)

@when('I scroll "(?P<direction>[^"]+)" in "(?P<app_alias>[^"]+)"')
def step_scroll(context, direction, app_alias):
    context.app_manager.interact_scroll(app_alias, direction)
