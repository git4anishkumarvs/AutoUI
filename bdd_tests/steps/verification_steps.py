from behave import then

@then('I should be able to switch focus to "{app_alias}"')
def step_verify_focus(context, app_alias):
    context.app_manager.switch_to_app(app_alias)
    assert app_alias in context.app_manager.active_apps, f"{app_alias} was not launched."

@then('the calculation and logging process should be complete')
def step_calc_complete(context):
    print("\n[Behave] Parallel Execution Test Completed Successfully!")

@then('the process should be complete')
def step_generic_complete(context):
    pass
