import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import * as api from '../services/api';

export default function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (!api.getToken()) {
      navigate('/login');
      return;
    }
    api
      .getCurrentUser()
      .then((data) => setUser(data.user))
      .catch(() => {
        api.clearToken();
        navigate('/login');
      });
  }, [navigate]);

  return (
    <div dir="rtl" className="flex min-h-screen bg-[#C8E8EB]">
      <Sidebar />

      <main className="flex-1 p-10">
        <h1 className="text-3xl font-extrabold text-[#094B50] mb-2">داشبورد</h1>
        {user ? (
          <p className="text-[#094B50] text-lg">
            خوش آمدی، <span className="font-bold">{user.username}</span> 👋
          </p>
        ) : (
          <p className="text-[#094B50]/60">در حال بارگذاری…</p>
        )}

        <div className="mt-8 bg-white/60 rounded-2xl p-6 max-w-xl">
          <p className="text-[#094B50] leading-8">
            از نوار کناری می‌توانی به هر میکروسرویس وارد شوی. مواردی که با برچسب
            «به‌زودی» مشخص شده‌اند هنوز توسط تیم‌ها پیاده‌سازی نشده‌اند.
          </p>
        </div>
      </main>
    </div>
  );
}
