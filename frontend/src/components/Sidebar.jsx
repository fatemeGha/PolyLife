import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../services/api';

export default function Sidebar() {
  const navigate = useNavigate();
  const [services, setServices] = useState([]);

  useEffect(() => {
    api
      .getMicroservices()
      .then((data) => setServices(data.microservices))
      .catch(() => setServices([]));
  }, []);

  const handleLogout = async () => {
    await api.logout();
    navigate('/login');
  };

  return (
    <aside
      dir="rtl"
      className="w-64 min-h-screen bg-[#094B50] text-[#FAEEDB] flex flex-col p-5 shadow-xl"
    >
      <h1 className="text-2xl font-extrabold tracking-wider mb-1">پلی‌لایف</h1>
      <p className="text-[#FAEEDB]/60 text-sm mb-6">میکروسرویس‌ها</p>

      <nav className="flex flex-col gap-2 flex-1">
        {services.map((s) =>
          s.implemented ? (
            <a
              key={s.slug}
              href={s.url}
              className="px-4 py-2 rounded-xl bg-[#FAEEDB]/10 hover:bg-[#FAEEDB]/20 transition font-medium"
            >
              {s.name}
            </a>
          ) : (
            <span
              key={s.slug}
              title="هنوز پیاده‌سازی نشده"
              className="px-4 py-2 rounded-xl bg-[#FAEEDB]/5 text-[#FAEEDB]/40 cursor-not-allowed flex items-center justify-between"
            >
              {s.name}
              <span className="text-[10px] border border-[#FAEEDB]/20 rounded px-1.5 py-0.5">
                به‌زودی
              </span>
            </span>
          )
        )}
        {services.length === 0 && (
          <span className="text-[#FAEEDB]/40 text-sm">موردی برای نمایش نیست</span>
        )}
      </nav>

      <button
        onClick={handleLogout}
        className="mt-4 px-4 py-2 rounded-xl bg-[#185E64] hover:bg-[#0D3D42] transition font-bold"
      >
        خروج
      </button>
    </aside>
  );
}
