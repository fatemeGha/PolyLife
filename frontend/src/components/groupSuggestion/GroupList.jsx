import { useEffect, useState } from "react";
import GroupCard from "./GroupCard";

function GroupList({ filters }) {

  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {

    if (!filters) return;

    const fetchGroups = async () => {

      setLoading(true);
      setError("");

      try {

        const response = await fetch("/api/groups/recommend", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(filters),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.message);
        }

        setGroups(data.groups || []);

      } catch (err) {

        setGroups([]);
        setError(err.message || "خطا در ارتباط با سرور");

      } finally {

        setLoading(false);

      }

    };

    fetchGroups();

  }, [filters]);

  if (!filters)
    return (
      <div className="text-gray-500">
        برای مشاهده گروه‌ها ابتدا فرم را تکمیل کنید.
      </div>
    );

  if (loading)
    return <p>در حال جستجوی گروه‌های مناسب...</p>;

  if (error)
    return (
      <div className="bg-red-100 text-red-700 rounded p-4">
        {error}
      </div>
    );

  if (groups.length === 0)
    return (
      <div className="text-gray-500">
        گروهی مطابق شرایط شما پیدا نشد.
      </div>
    );

  return (

    <div>

      <h2 className="text-2xl font-bold mb-5">
        گروه‌های پیشنهادی
      </h2>

      <div className="space-y-5">

        {groups.map(group => (

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