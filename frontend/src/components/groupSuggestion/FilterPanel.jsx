import { useState } from "react";

function FilterPanel({ onSearch }) {
  const [formData, setFormData] = useState({
    goalId: "",
    fitnessLevel: "",
    workoutType: "",
    availableDays: [],
    equipment: [],
    preferredStartTime: "",
    preferredEndTime: "",
    injuries: [],
  });

  const [error, setError] = useState("");

  const days = [
    "Saturday",
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
  ];

  const workoutTypes = [
    "Gym",
    "Running",
    "Swimming",
    "Cycling",
    "Yoga",
    "HIIT",
    "CrossFit",
    "Home Workout",
  ];

  const fitnessLevels = [
    "Beginner",
    "Intermediate",
    "Advanced",
  ];

  const handleChange = (e) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const toggleDay = (day) => {
    setFormData((prev) => ({
      ...prev,
      availableDays: prev.availableDays.includes(day)
        ? prev.availableDays.filter((d) => d !== day)
        : [...prev.availableDays, day],
    }));
  };

  const handleSubmit = () => {
    if (
      !formData.goalId ||
      !formData.fitnessLevel ||
      !formData.workoutType
    ) {
      setError("تمام فیلدهای ضروری را تکمیل کنید.");
      return;
    }

    setError("");
    onSearch(formData);
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">

      <h2 className="text-2xl font-bold mb-6">
        اطلاعات شما
      </h2>

      {error && (
        <div className="mb-4 rounded bg-red-100 text-red-700 p-3">
          {error}
        </div>
      )}

      <div className="space-y-5">

        <div>
          <label>Goal</label>

          <input
            className="w-full border rounded p-2"
            name="goalId"
            value={formData.goalId}
            onChange={handleChange}
          />
        </div>

        <div>

          <label>Fitness Level</label>

          <select
            className="w-full border rounded p-2"
            name="fitnessLevel"
            value={formData.fitnessLevel}
            onChange={handleChange}
          >
            <option value="">Select</option>

            {fitnessLevels.map(level => (
              <option
                key={level}
                value={level}
              >
                {level}
              </option>
            ))}

          </select>

        </div>

        <div>

          <label>Workout Type</label>

          <select
            className="w-full border rounded p-2"
            name="workoutType"
            value={formData.workoutType}
            onChange={handleChange}
          >

            <option value="">Select</option>

            {workoutTypes.map(type => (
              <option
                key={type}
                value={type}
              >
                {type}
              </option>
            ))}

          </select>

        </div>

        <div>

          <label className="block mb-2">
            Available Days
          </label>

          <div className="grid grid-cols-2 gap-2">

            {days.map(day => (

              <label
                key={day}
                className="flex gap-2"
              >
                <input
                  type="checkbox"
                  checked={formData.availableDays.includes(day)}
                  onChange={() => toggleDay(day)}
                />
                {day}
              </label>

            ))}

          </div>

        </div>

        <div className="grid grid-cols-2 gap-3">

          <div>

            <label>Start</label>

            <input
              type="time"
              name="preferredStartTime"
              value={formData.preferredStartTime}
              onChange={handleChange}
              className="w-full border rounded p-2"
            />

          </div>

          <div>

            <label>End</label>

            <input
              type="time"
              name="preferredEndTime"
              value={formData.preferredEndTime}
              onChange={handleChange}
              className="w-full border rounded p-2"
            />

          </div>

        </div>

        <button
          onClick={handleSubmit}
          className="w-full bg-blue-600 text-white rounded py-2"
        >
          Find Groups
        </button>

      </div>

    </div>
  );
}

export default FilterPanel;