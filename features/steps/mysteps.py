from behave import *
import behave
from another_lib.steps import *
from my_package import return_foo

runtime_matcher = behave.matchers.current_matcher

print('\nmysteps runtime matcher: ', runtime_matcher, end='\n\n')

# As a user, I expect the matcher is the default parse
# But this will fail because another_lib changes the parser to re
@then(u'I expect that return_foo returns "{expected}"')
def check_foo(context, expected):
    result = return_foo()
    assert result == expected, 'Expected {} but got {}'.format(expected, result)


# The following is provided as a meta tool for assessing the core problem

@step(u'I expect the runtime matcher is "([^"]*)?"')
@then(u'I expect the runtime matcher is "{expected_matcher}"')
def check_matcher(context, expected_matcher):
    reverse_matcher_names = {'ParseMatcher': 'parse',
                           'CFParseMatcher': 'cfparse',
                           'RegexMatcher': 're'}

    class_name = runtime_matcher.__name__
    matcher = reverse_matcher_names[class_name]
    assert expected_matcher == matcher, 'Expected the matcher was {} but it was {}'.format(expected_matcher,
                                                                                           matcher)