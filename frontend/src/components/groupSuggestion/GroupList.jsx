import { useEffect, useState } from "react";
import GroupCard from "./GroupCard";


function GroupList({ filters }) {


  const [groups,setGroups] = useState([]);

  const [loading,setLoading] = useState(false);

  const [error,setError] = useState("");



  useEffect(()=>{


    if(!filters)
      return;



    async function loadGroups(){


      try {

        setLoading(true);
        setError("");


        const response = await apiRequest(
          "/groups/recommend",
          {
            method:"POST",

            body:JSON.stringify(filters)
          }
        );


        setGroups(
          response.data.groups
        );


      }

      catch(err){

        setGroups([]);

        setError(err.message);

      }

      finally{

        setLoading(false);

      }


    }


    loadGroups();


  },[filters]);



  if(loading)
    return (
      <p>
        در حال جستجوی گروه مناسب...
      </p>
    );



  if(error)

    return (

      <div className="text-red-600 border p-3 rounded">

        {error}

      </div>

    );



  if(groups.length===0)

    return (

      <p className="text-gray-500">

        گروه مناسبی پیدا نشد.

      </p>

    );



  return (

    <div>


      <h2 className="text-xl font-bold mb-5">

        گروه‌های پیشنهادی

      </h2>



      <div className="space-y-4">


        {
          groups.map(group=>(

            <GroupCard
              key={group.id}
              group={group}
            />

          ))
        }


      </div>


    </div>

  );


}


export default GroupList;