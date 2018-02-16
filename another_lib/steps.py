from behave import *
import behave

use_step_matcher('re')
@given(u'I( do not)* use a step library')
def step_impl(context, not_):
	pass
	
