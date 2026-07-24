import {
  workoutTypeLabels,
  difficultyLabels,
  riskLabels,
  goalLabels
}
from "./constants/labels";



function GroupCard({group}) {


return (

<div className="border rounded-xl p-5 shadow-sm">


<h3 className="text-xl font-bold mb-3">

{group.name}

</h3>



<p>
هدف:
{
 goalLabels[group.goal.name]
 ||
 group.goal.name
}
</p>



<p>
نوع تمرین:
{
 workoutTypeLabels[group.workout_type]
}
</p>



<p>
سطح سختی:
{
 difficultyLabels[group.difficulty_level]
}
</p>



<p>
زمان:

{group.start_time}

تا

{group.end_time}

</p>



<p>
اعضا:

{group.member_count}

از

{group.max_members}

</p>



<p>

امتیاز تطبیق:

{group.match_score}%

</p>



<p>

سطح ریسک:

<span>

{
riskLabels[group.risk.level]
}

</span>

</p>



<button

className="
mt-4
px-5
py-2
bg-blue-600
text-white
rounded
"

>

مشاهده جزئیات

</button>



</div>


);


}


export default GroupCard;