window.addEventListener("DOMContentLoaded", loadReports);

async function loadReports(){

    const summary = await api("/reports/summary/");
    const users = await api("/reports/users/");
    const workouts = await api("/reports/workouts/");

    document.getElementById("totalExercises").innerText =
        summary.total_exercises;

    document.getElementById("totalPrograms").innerText =
        summary.total_programs;

    document.getElementById("totalHistory").innerText =
        summary.total_histories;

    document.getElementById("activeUsers").innerText =
        users.active_users;

    drawSummary(summary);

    drawWorkoutChart(workouts);

}

function drawSummary(summary){

    new Chart(

        document.getElementById("summaryChart"),

        {

            type:"bar",

            data:{

                labels:[

                    "تمرین",

                    "برنامه",

                    "علاقه‌مندی",

                    "سوابق"

                ],

                datasets:[{

                    label:"تعداد",

                    data:[

                        summary.total_exercises,

                        summary.total_programs,

                        summary.total_favorites,

                        summary.total_histories

                    ]

                }]

            }

        }

    );

}

function drawWorkoutChart(data){

    new Chart(

        document.getElementById("workoutChart"),

        {

            type:"pie",

            data:{

                labels:data.map(x=>x.workout__title),

                datasets:[{

                    data:data.map(x=>x.times)

                }]

            }

        }

    );

}