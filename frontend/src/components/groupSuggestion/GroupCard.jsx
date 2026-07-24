function GroupCard({ group }) {

  const riskColor = {
    Low: "text-green-600",
    Medium: "text-yellow-600",
    High: "text-red-600",
  };

  return (

    <div className="border rounded-xl p-5 shadow-sm">

      <div className="flex justify-between">

        <div>

          <h3 className="text-xl font-bold">
            {group.name}
          </h3>

          <p>
            Goal : {group.goal_name}
          </p>

          <p>
            Workout : {group.workout_type}
          </p>

          <p>
            Difficulty : {group.difficulty_level}
          </p>

          <p>
            Members : {group.member_count}/{group.max_members}
          </p>

          <p className={riskColor[group.risk_level]}>
            Risk : {group.risk_level}
          </p>

        </div>

        <div className="flex flex-col justify-end gap-3">

          <button
            className="px-5 py-2 border rounded hover:bg-gray-100"
          >
            View Details
          </button>

          <button
            className="px-5 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Join
          </button>

        </div>

      </div>

    </div>

  );

}

export default GroupCard;