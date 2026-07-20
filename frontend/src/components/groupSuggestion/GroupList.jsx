import GroupCard from "./GroupCard";

const groups = [
  {
    id:1,
    name:"گروه آمادگی جسمانی",
    goal:"افزایش آمادگی",
    level:"مبتدی",
    time:"شنبه ۱۸",
    members:12
  },
  {
    id:2,
    name:"گروه کاهش وزن",
    goal:"کاهش وزن",
    level:"متوسط",
    time:"یکشنبه ۲۰",
    members:8
  },
  {
    id:3,
    name:"گروه یوگا",
    goal:"انعطاف",
    level:"همه",
    time:"دوشنبه ۱۷",
    members:15
  }
];

function GroupList() {
  return (
    <div>

      <h2 className="text-xl font-bold mb-5">
        گروه‌های پیشنهادی
      </h2>

      <div className="space-y-4">

        {groups.map(group=>(
          <GroupCard
            key={group.id}
            group={group}
          />
        ))}

      </div>

    </div>
  );
}

export default GroupList;