function GroupCard({ group }) {
  return (
    <div className="border rounded-lg p-4 flex justify-between items-center">

      <div className="flex gap-4">

        <div className="w-24 h-24 border rounded bg-gray-100"></div>

        <div>

          <h3 className="font-bold text-lg">
            {group.name}
          </h3>

          <p>هدف: {group.goal}</p>
          <p>سطح: {group.level}</p>
          <p>زمان: {group.time}</p>
          <p>اعضا: {group.members}</p>

        </div>

      </div>

      <button className="border rounded px-5 py-2 hover:bg-gray-100">
        مشاهده جزئیات
      </button>

    </div>
  );
}

export default GroupCard;