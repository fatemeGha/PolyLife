from django.db import models

# Your team's data models go here. They live in YOUR database (the core's
# router routes "team2" models to the "team2" database automatically).
#
# Link rows to the logged-in user by their core id — store the id, do NOT add a
# ForeignKey to the core User (it lives in a different database).
#
# Example (uncomment and adapt):
#
# class Note(models.Model):
#     user_id = models.IntegerField(db_index=True)   # comes from X-User-Id
#     text = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)
