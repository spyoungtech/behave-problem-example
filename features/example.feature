Feature: use a step library
    As a behave user
    I want to use step implementations written by others in combination with my own.

    Scenario: I can use the step library steps just by importing them
      Given I use a step library

    Scenario: My standalone steps should work the same regardless of whether I use imported a step library
        Then I expect that return_foo returns "foo"

    Scenario: I can use a step library along with my own steps, even if they don't use my matcher
        Given I use a step library
        Then I expect that return_foo returns "foo"

    Scenario: The matcher is not changed importing a step library (meta)
        Given I use a step library
        Then I expect the runtime matcher is "parse"