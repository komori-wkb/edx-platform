"""Models for ga_task"""

import json
from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models, transaction


# define custom states used by ContractTask
QUEUING = 'QUEUING'
PROGRESS = 'PROGRESS'


class Task(models.Model):
    """
    Stores information about background tasks that have been submitted to perform work.

    `task_type` identifies the kind of task being performed, e.g. personalinfo_mask
    `task_key` stores relevant input arguments encoded into key value for testing to see
        if the task is already running (together with task_type). The caller must be created to be unique.
    `task_input` stores input arguments as JSON-serialized dict, for reporting purposes.
    `task_id` stores the id used by celery for the background task.
    `task_state` stores the last known state of the celery task
    `task_output` stores the output of the celery task.
        Format is a JSON-serialized dict.  Content varies by task_type and task_state.
    `requester` stores id of user who submitted the task
    `created` stores date that entry was first created
    `updated` stores date that entry was last modified
    """
    task_type = models.CharField(max_length=50, db_index=True)
    task_key = models.CharField(max_length=255, db_index=True)
    task_input = models.CharField(max_length=255)
    task_id = models.CharField(max_length=255, db_index=True)  # max_length from celery_taskmeta
    task_state = models.CharField(max_length=50, db_index=True)  # max_length from celery_taskmeta
    task_output = models.CharField(max_length=1024, null=True)
    requester = models.ForeignKey(User, db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    subtasks = models.TextField(blank=True)  # JSON dictionary

    class Meta:
        app_label = 'ga_task'

    @classmethod
    def create(cls, task_type, task_key, task_input, requester):
        """
        Create an instance of Task.
        """
        # create the task_id here, and pass it into celery:
        task_id = str(uuid4())

        json_task_input = json.dumps(task_input)

        # check length of task_input, and return an exception if it's too long:
        if len(json_task_input) > 255:
            raise ValueError(
                "Task input longer than 255: {task_input} for {task_type}".format(
                    task_input=json_task_input, task_type=task_type
                )
            )

        # create the task, then save it:
        task = cls(
            task_type=task_type,
            task_key=task_key,
            task_input=json_task_input,
            task_id=task_id,
            task_state=QUEUING,
            requester=requester
        )
        task.save_now()

        return task

    @transaction.atomic
    def save_now(self):
        """
        Writes Task immediately, ensuring the transaction is committed.

        Autocommit annotation makes sure the database entry is committed.
        When called from any view that is wrapped by TransactionMiddleware,
        and thus in a "commit-on-success" transaction, this autocommit here
        will cause any pending transaction to be committed by a successful
        save here.  Any future database operations will take place in a
        separate transaction.
        """
        self.save()

    @staticmethod
    def create_output_for_success(returned_result):
        """
        Converts successful result to output format.

        Raises a ValueError exception if the output is too long.
        """
        # In future, there should be a check here that the resulting JSON
        # will fit in the column.  In the meantime, just return an exception.
        json_output = json.dumps(returned_result)
        if len(json_output) > 1023:
            raise ValueError("Length of task output is too long: {0}".format(json_output))
        return json_output

    @staticmethod
    def create_output_for_failure(exception, traceback_string):
        """
        Converts failed result information to output format.

        Traceback information is truncated or not included if it would result in an output string
        that would not fit in the database.  If the output is still too long, then the
        exception message is also truncated.

        Truncation is indicated by adding "..." to the end of the value.
        """
        tag = '...'
        task_progress = {'exception': type(exception).__name__, 'message': unicode(exception.message)}
        if traceback_string is not None:
            # truncate any traceback that goes into the Task model:
            task_progress['traceback'] = traceback_string
        json_output = json.dumps(task_progress)
        # if the resulting output is too long, then first shorten the
        # traceback, and then the message, until it fits.
        too_long = len(json_output) - 1023
        if too_long > 0:
            if traceback_string is not None:
                if too_long >= len(traceback_string) - len(tag):
                    # remove the traceback entry entirely (so no key or value)
                    del task_progress['traceback']
                    too_long -= (len(traceback_string) + len('traceback'))
                else:
                    # truncate the traceback:
                    task_progress['traceback'] = traceback_string[:-(too_long + len(tag))] + tag
                    too_long = 0
            if too_long > 0:
                # we need to shorten the message:
                task_progress['message'] = task_progress['message'][:-(too_long + len(tag))] + tag
            json_output = json.dumps(task_progress)
        return json_output