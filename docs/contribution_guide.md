## Getting started

Make sure you have a Github account.

## Making functional changes

These are the changes that alter the functional behavior of the product.

**Workflow**:

1. Submit a Github issue if one does not already exist.
    * Make sure you fill in the earliest version that you know has the issue.
    * An issue should contain these sections:
        - *Description*.
          Describe the issue including steps to reproduce when it is a bug.
        - *Acceptance Criteria*.
          Describe the expected behavior.
    * An issue might contain these sections:
        - *Task breakdown*.
          These are the steps the task implementation should be split into.
          Each step could be merged via separate Merge Request.
    * An issue is not necessary for [Trivial changes](#making-trivial-changes)
2. Create a working branch from the branch you want to base your work on.
      * This is usually the `develop` branch.
      * Only target release branches if you are certain your fix must be on that
        branch.
      * Please avoid working directly on the `master`  or `develop` branch.
      * Please name your branch, using pattern `issues/<ID>`.
3. Make commits of logical and atomic units to your working branch.
4. Make sure you have added the necessary unit-tests for your changes.
   Not all cases require adding unit-tests.
   It's up to you and your experience to decide when to add them.
   Our reviewers might request you to add them.
5. Check that all unit-tests pass successfully, both new unit-tests and already existing ones.

       From sipplauncher directory run:

            make install-all
            make install-reqs-test
            make test

6. Add your feature description to documentation, if this is relevant.
   Documentation is located at `sipplauncher/docs` folder.

       You'll be able to preview your documentation changes in the browser location `http://<ip_address>:8000/`.
       For this, run documentation server from sipplauncher directory:

           make install-reqs-docs
           make docs_serve

7. Add initial Merge Request of your branch into the target branch.
   Merge Request should be named `WIP: Issue #<issue_number>: <issue_description>`.
   WIP (Work in progress) notifies other developers, that it's too early to review or merge it.
8. Review your Merge Request.
   Try to put yourself at the place of the reviewer.
   Will the changes proposed there be easily understandable for the reviewer?
9. Make your Merge Request as small as possible.
   It's very hard for a reviewer to review a big diff, which contains lots of irrelevant changes.
   And usually this way new bugs enter the software - they simply leave unnoticed in tons of new code.
   Therefore, it's essential to make Merge Request as small as possible.
   To achieve this:
       * Decouple [Trivial changes](#making-trivial-changes) and merge them via separate Merge requests
       * Remove irrelevant changes from Merge Request.
         We understand that it might be tempting to fix everything as you go.
         But please don't do this!
         The changes in your Merge Request should relate only to the description of the Github issue.
         If you see something bad in adjacent code, please open an issue in Github and work on it later.

10. Remove the `WIP: ` prefix from the Merge Request.
12. Ask the project maintainer (or some other developer working on the project) to review the Merge Request.
13. Please be polite to a reviewer.
    Remember that reviewing another person's code is usually harder than writing your own.
14. If you have an insurmountable dispute with a reviewer, please add a 3rd person to your discussion to judge.
15. After the Merge Request has been approved by at least 1 person, merge the code.
16. Close the Github issue.

## Making trivial changes

These are the changes that don't alter the functional behavior of the product.

They are one of the following:

* Adding, changing or deleting a comment.
* Removing unused variables.
* Changing code formatting (changing text intentation, adding or removing white-spaces, etc).
* Changing logging content, adding or removing logging.
* Changing function or class names.
* Other small changes (several lines of code) that don't change the functional behavior of the product.

The **workflow** for trivial changes contains only several action items from the [full workflow](#making-functional-changes):

1. Create a working branch from the branch you want to base your work on.
2. Make commit.
   Start the first line of a commit with `trivial: <issue_description>`.
3. Check that all existing unit-tests pass successfully.
4. Add Merge Request of your branch into the target branch.
   Merge Request should be named `trivial: <issue_description>`.
5. Merge it.

Code review is not required for such changes to be merged.
