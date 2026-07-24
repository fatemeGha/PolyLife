from django.contrib import admin

from .models import (
	Exercise,
	WorkoutProgram,
	WorkoutExercise,
	UserPreference,
	Favorite,
	WorkoutHistory,
)


admin.site.register(Exercise)
admin.site.register(WorkoutProgram)
admin.site.register(WorkoutExercise)
admin.site.register(UserPreference)
admin.site.register(Favorite)
admin.site.register(WorkoutHistory)
