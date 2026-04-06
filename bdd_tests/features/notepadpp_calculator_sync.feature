Feature: Mirror Paint Text Input Into Calculator

  As an automation tester
  I want to type an expression into Paint using a text control
  And mirror the same sequence into Calculator
  So that I can verify cross-application synchronization using visual grounding.

  Scenario: Type 52+7= into Paint and mirror it into Calculator
    Given the AppManager is initialized
    When I launch "mspaint.exe" as "EditorApp"
    And I launch "calc.exe" as "CalcApp"
    And I wait for 2 seconds

    When I switch focus to "EditorApp"
    And I type "5" into "Text area" identified by "vlm" in "EditorApp"
    And I switch focus to "CalcApp"
    And I click on "5" identified by "vlm" in "CalcApp"

    When I switch focus to "EditorApp"
    And I type "2" into "Text area" identified by "vlm" in "EditorApp"
    And I switch focus to "CalcApp"
    And I click on "2" identified by "vlm" in "CalcApp"

    When I switch focus to "EditorApp"
    And I type "+" into "Text area" identified by "vlm" in "EditorApp"
    And I switch focus to "CalcApp"
    And I click on "+" identified by "vlm" in "CalcApp"

    When I switch focus to "EditorApp"
    And I type "7" into "Text area" identified by "vlm" in "EditorApp"
    And I switch focus to "CalcApp"
    And I click on "7" identified by "vlm" in "CalcApp"

    When I switch focus to "EditorApp"
    And I type "=" into "Text area" identified by "vlm" in "EditorApp"
    And I switch focus to "CalcApp"
    And I click on "=" identified by "vlm" in "CalcApp"

    Then the process should be complete
