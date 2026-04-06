Feature: Calculator Addition

  As an automation tester
  I want to open Calculator and enter a simple expression
  So that I can verify VLM-driven calculator interaction works end to end.

  Scenario: Open Calculator and enter 5 + 7 =
    Given the AppManager is initialized
    When I launch "calc.exe" as "CalcApp"
    And I wait for 2 seconds
    And I switch focus to "CalcApp"
    And I click on "5" identified by "vlm" in "CalcApp"
    And I click on "+" identified by "vlm" in "CalcApp"
    And I click on "7" identified by "vlm" in "CalcApp"
    And I click on "=" identified by "vlm" in "CalcApp"
    Then the process should be complete
