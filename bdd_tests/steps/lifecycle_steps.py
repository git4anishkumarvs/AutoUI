import time
from behave import given, when

@given('the AppManager is initialized')
def step_init_manager(context):
    assert hasattr(context, 'app_manager') and context.app_manager is not None, "AppManager missing."
    print("\n[Behave] AppManager is active.")

@when('I launch "{app_path}" as "{app_alias}"')
def step_launch_app_as(context, app_path, app_alias):
    context.app_manager.launch_app(app_alias, app_path=app_path)

@when('I launch "{app_alias}"')
def step_launch_app(context, app_alias):
    # Fallback for implicit launching if the alias IS the path
    try:
        context.app_manager.launch_app(app_alias)
    except ValueError:
        context.app_manager.launch_app(app_alias, app_path=app_alias)

@when('I terminate "{app_alias}"')
def step_terminate_app(context, app_alias):
    if app_alias in context.app_manager.active_apps:
        context.app_manager.active_apps[app_alias].terminate()
        del context.app_manager.active_apps[app_alias]

@when('I switch focus to "{app_alias}"')
def step_switch_focus(context, app_alias):
    context.app_manager.switch_to_app(app_alias)

@when('I wait for {seconds:d} seconds')
def step_wait(context, seconds):
    time.sleep(seconds)
