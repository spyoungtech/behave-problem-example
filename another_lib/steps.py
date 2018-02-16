from behave import *
import behave
original_matcher = behave.matchers.current_matcher

use_step_matcher('re')
@given(u'I( do not)* use a step library')
def step_impl(context, not_):
	pass
	

behave.matchers.current_matcher = original_matcher