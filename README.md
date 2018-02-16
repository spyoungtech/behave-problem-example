# What is this?
This is, in part, a springboard for creating guidelines and best-practices for behave step library writers. For the 
moment, this only briefly describes some underlying ideas and concepts while the bulk explains a problem 
that arises in designing a step library and provides a long-winded narrative of arriving at possible solutions.

For the purposes of this example `another_lib` is provided in the working directory so the example is executable, 
however in practice the idea is this library would be installed to the users site-packages.


## Premise

The idea behind this premise is to provide behave users a beautiful API for using step libraries. This rests on some 
assumptions about how step library writers 'ought to provide step definitions and certain freedoms 
users of those libraries should have. Here's the top five that come to mind:

- Users of step libraries should be able to import the provided step definitions directly into their own step files. 
- Users may use multiple step libraries
- Users should be able to easily and cleanly modify behaviors of the step library.
- Authors of large libraries may provide namespaced step definitions to allow importing just a subset of all the library steps, I.E. 
`step_library.domain.steps` could be imported and registered without also registering `step_library.other_domain.steps`
- It's hard to extend module-level functions. As such, it's ideal if the definitions in a step library delegate as much work as possible to user-extendable interfaces elsewhere in the library.


The step library I author, [behave-webdriver](https://github.com/spyoungtech/behave-webdriver), (a work-in-progress) 
is designed with these ideas in mind.


# A key problem with importable step definitions

The behave matcher uses global state. As such, a library writer can unexpectedly modify this 
global state to the detriment of the user **and vice versa**.

Despite the fact that behave [attempts to manage this problem of gloabl state](https://github.com/behave/behave/blob/master/behave/runner_util.py#L389-L413) 
when loading the step modules, this does not fix the problem of global state being modified when the step module 
imports a step library to register steps.

In light of this, library writers must bear the burden of carefully managing this global state 
to avoid altering how user code would otherwise behave.

[About global state](https://softwareengineering.stackexchange.com/questions/148108/why-is-global-state-so-evil).


# The problem demonstrated


The master branch is in state where the tests of `my_package` are broken because of global state changed by `another_lib`.  
Remember that `another_lib` is only provided directly in the repository as a convenience; 
the idea is that step libraries would be contained in the user's installed packages.

The only thing you need to run this is behave v1.2.5


## The results

```
$ behave

mysteps runtime matcher:  <class 'behave.matchers.RegexMatcher'>

Feature: use a step library # features\example.feature:1
  As a behave user
  I want to use step implementations written by others in combination with my own.
  Scenario: I can use the step library steps just by importing them  # features\example.feature:5
    Given I use a step library                                       # another_lib\steps.py:5

  Scenario: My standalone steps should work the same regardless of whether I use imported a step library  # features\example.feature:8
    Then I expect that return_foo returns "foo"                                                           # None

  Scenario: I can use a step library along with my own steps, even if they don't use my matcher  # features\example.feature:11
    Given I use a step library                                                                   # another_lib\steps.py:5
    Then I expect that return_foo returns "foo"                                                  # None

  Scenario: The matcher is not changed importing a step library (meta)  # features\example.feature:15
    Given I use a step library                                          # another_lib\steps.py:5
    Then I expect the runtime matcher is "parse"                        # features\steps\mysteps.py:20
      Assertion Failed: Expected the matcher was parse but it was re



Failing scenarios:
  features\example.feature:8  My standalone steps should work the same regardless of whether I use imported a step library
  features\example.feature:11  I can use a step library along with my own steps, even if they don't use my matcher
  features\example.feature:15  The matcher is not changed importing a step library (meta)

0 features passed, 1 failed, 0 skipped
1 scenario passed, 3 failed, 0 skipped
3 steps passed, 1 failed, 0 skipped, 2 undefined
Took 0m0.001s

You can implement step definitions for undefined steps with these snippets:

@then(u'I expect that return_foo returns "foo"')
def step_impl(context):
    raise NotImplementedError(u'STEP: Then I expect that return_foo returns "foo"')

```

### Breaking it down

The first thing you'll notice is the debug print showing that the matcher was the `RegexMatcher`, which was indeed set 
by the step library.

This means that the user-provided step definition
```python
@then(u'I expect that return_foo returns "{expected}"')
```
will not match, therefore behave assumes the step in the feature file is undefined, so the first two scenarios fail. 
Also notice we identify that the matcher was, in fact, not the expected 'parse', but 're'

```
  Scenario: The matcher is not changed by misbehaving library (meta)  # features\example.feature:12
    Given I use a misbehaving library                                 # another_lib\steps.py:5
    Then I expect the runtime matcher is "parse"                      # features\steps\mysteps.py:20
      Assertion Failed: Expected the matcher was parse but it was re
```


# Proposed solution

The burden of solving this problem (in this authors view) should lie squarely on the shoulders of step library writers. 

Step library writers should attempt to return the global state to its previous state prior to the library import. 
The basic idea is as follows.

- identify the matcher in use before modifying the matcher
- Always explicitly set the matcher they use, because a user (or basically any package) could have modified the global state before importing the library steps
- at the end of each step module, set the matcher to the matcher that was previously identified



## Obstacles

- The only 'public' interface for altering the matcher is `use_step_matcher`.
- There is no public interface for identifying the *name* of the current matcher for use with `use_step_matcher`

## Possible Solutions: a progression of ideas


### Band-aid

To get around this, the current method is to set the matcher to the default by calling `use_step_matcher('parse')` at the end of 
step modules in the step library. This strictly uses behave's public interfaces to attempt to alleviate the problem.

```python
# site-packages/step_library/somewhere/some_steps.py
from behave import *
# always set the matcher explicitly
use_step_matcher('some_matcher') # we can never be confident of the global state to begin with.

# write step definitions here

# set the matcher back to the default at the end of the module
use_step_matcher('parse') # perhaps there's a way to identify the default module if changed in user's environment.py
```

However, this is not entirely adequate because the user may not necesarily be using the parse matcher at the time 
the step library is imported.


### Band-aid+

Instead of blindly setting the matcher back to the parse matcher, we can try to figure out which matcher was being used 
when our step library was imported so we can set it back later at the end of our module. Though, this means we need to 
dig a little deeper into behave's API.
 
The current matcher *class* can be retrieved via inspecting the global state `behave.matchers.current_matcher`. 
Unfortunately, there's no concrete way to get a string out of the matcher class to use with `use_step_matcher` 
We can, however, use our knowledge of the matchers provided by behave to at least cover those.

The following is an example of a function that does this
```python
# ...step_library/utils.py
import behave
def get_matcher_name(default=None):
    """
    A hack to inspect the global state to return a name suitable for use with ``use_step_matcher`` 
    Only works if the current matcher is a matcher provided by behave.
    
    :param default: if the name cannot be found, return this instead. If not provided, a KeyError will be raised.
    :raises: KeyError
    """
    
    name_map = {'ParseMatcher': 'parse',
                'CFParseMatcher': 'cfparse',
                'RegexMatcher': 're'}
    matcher_class = behave.matchers.current_matcher
    class_name = matcher_class.__name__
    matcher_name = name_map.get(class_name, default)
    if matcher_name is None:
        raise KeyError('Could not determine a name for class {matcher_class}')
    return matcher_name
```

Applying this idea on top of the previous example, still only using the public `use_step_matcher` to make any *changes* to the state, we might do something like this

```python
# site-packages/step_library/somewhere/some_steps.py
from behave import *
from step_library.utils import get_matcher_name

# Before changing anything, check the global state and identify the original matcher by name.
original_matcher_name = get_matcher_name()


# always set the matcher explicitly
use_step_matcher('some_matcher') # we can never be confident of the global state to begin with.

# write your step definitions here

# set the matcher back to the original
use_step_matcher(original_matcher_name)
```

So, we increased the complexity of our solution somewhat by relying on some of behave's internal API, and we gained 
some resiliency and covered cases for those using a behave-provided matcher, and we still only use behave's public 
interfaces for *modifying* the global state. 

However, this is still incomplete if we consider users who may use a custom matcher.

### Complete* solution

Following the same idea, we can cover custom matchers too. Instead of getting the name from the current matcher, 
we simply get the matcher class then, at the end of the module, monkey patch the global state back to the original matcher 
after the step library steps are registered. 

This ensures users will not have any surprises by importing the library.

```python
# some_library/steps/libsteps.py
from behave import *
import behave

# save the original matcher before doing anything else
original_matcher = behave.matchers.current_matcher

# always do this, because the matcher may have been changed by a user or misbehaving library
use_step_matcher('some_matcher') 

# write step definitions here

# restore the original matcher at the end of the module by modifying the global state
behave.matchers.current_matcher = original_matcher # not ideal, but it works
```

*There is a cost here, however, because we are taking global state management into our own hands through a 
less-than-public interface. So, we risk the fact that an implementation change in `behave` can break this code, possibly 
with little to no warning. If you take this approach, you, as a behave superuser, are encouraged to watch the 
[behave](https://github.com/behave/behave) project closely for upcoming changes and further, contribute to changes that 
make the behave ecosystem more flexible for its extenders.

## New results with any of these solutions applied

If you apply the changes (available in the `solution-applied` branch) you'll see that we address the problem for the user 
and all the tests pass.

```
$ git checkout solution-applied
$ behave

mysteps runtime matcher:  <class 'behave.matchers.ParseMatcher'>

Feature: use a step library # features\example.feature:1
  As a behave user
  I want to use step implementations written by others in combination with my own.
  Scenario: I can use the step library steps just by importing them  # features\example.feature:5
    Given I use a step library                                       # another_lib\steps.py:6

  Scenario: My standalone steps should work the same regardless of whether I use imported a step library  # features\example.feature:8
    Then I expect that return_foo returns "foo"                                                           # features\steps\mysteps.py:12

  Scenario: I can use a step library along with my own steps, even if they don't use my matcher  # features\example.feature:11
    Given I use a step library                                                                   # another_lib\steps.py:6
    Then I expect that return_foo returns "foo"                                                  # features\steps\mysteps.py:12

  Scenario: The matcher is not changed importing a step library (meta)  # features\example.feature:15
    Given I use a step library                                          # another_lib\steps.py:6
    Then I expect the runtime matcher is "parse"                        # features\steps\mysteps.py:20

1 feature passed, 0 failed, 0 skipped
4 scenarios passed, 0 failed, 0 skipped
6 steps passed, 0 failed, 0 skipped, 0 undefined
Took 0m0.001s
```