Feature: Autonomous Vision-Language Multi-App Orchestration

  As an automation tester
  I want to calculate 5 + 3 = 8 using the Windows Calculator app
  And log each step dynamically into MSPaint using purely AI spatial reasoning
  So that I can verify parallel cross-application execution without hardcoded coordinate layouts.

  Scenario: Calculate 5 + 3 and log synchronously using purely Visual Grounding
    Given the AppManager is initialized
    When I launch "calc.exe" as "App2"
    And I launch "mspaint.exe" as "App1"
    And I wait for 2 seconds
    
    # 1. Click 5 
    When I switch focus to "App2"
    And I click on "5" identified by "vlm" in "App2"
    And I switch focus to "App1"
    And I type "5" into "Typing area" identified by "vlm" in "App1"

    # 2. Click +
    When I switch focus to "App2"
    And I click on "+" identified by "vlm" in "App2"
    And I switch focus to "App1"
    And I type " + " into "Typing area" identified by "vlm" in "App1"

    # 3. Click 3 (Resolving to result 8)
    When I switch focus to "App2"
    And I click on "3" identified by "vlm" in "App2"
    And I switch focus to "App1"
    And I type "3" into "Typing area" identified by "vlm" in "App1"

    # 4. Click = and finalize logging
    When I switch focus to "App2"
    And I click on "=" identified by "vlm" in "App2"
    And I switch focus to "App1"
    And I type " = 8" into "Typing area" identified by "vlm" in "App1"

    Then the calculation and logging process should be complete
