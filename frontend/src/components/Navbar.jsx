// src/components/Navbar.jsx
import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const location = useLocation();
  const menuItems = ["ارتباط با ما", "منابع", "داستان های موفقیت", "خدمات"];

  // تشخیص صفحه فعلی
  const isLoginPage = location.pathname === '/login';
  const isRegisterPage = location.pathname === '/register';
  const isHomePage = location.pathname === '/';

  return (
    <nav className="fixed top-6 left-6 right-6 z-50 flex items-center justify-between px-6 py-2 bg-white/10 backdrop-blur-lg border border-white/20 rounded-full shadow-2xl">
      
      {/* سمت چپ */}
      <div className="flex items-center gap-2">
        {isHomePage ? (
          <Link to="/register">
            <div className="bg-white p-2 rounded-full cursor-pointer hover:bg-gray-100 transition shadow-inner">
              <svg className="w-5 h-5 text-black" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 10a4 4 0 100-8 4 4 0 000 8zM2 18a8 8 0 0116 0H2z" />
              </svg>
            </div>
          </Link>
        ) : (
          <Link to="/">
            <div className="bg-white p-2 rounded-full cursor-pointer hover:bg-gray-100 transition shadow-inner">
              <svg className="w-5 h-5 text-black" fill="currentColor" viewBox="0 0 24 24">
                <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z" />
              </svg>
            </div>
          </Link>
        )}
      </div>

      {/* وسط: منو به رنگ سفید */}
      <div className="flex items-center gap-6">
        {menuItems.map((item, index) => (
          <a key={index} href="#" className="text-white font-medium hover:text-[#FDE6C3] transition duration-300 text-sm">
            {item}
          </a>
        ))}
      </div>

      {/* سمت راست */}
      <Link to={isLoginPage ? "/login" : "/register"}>
        <div className="text-white font-semibold px-4 py-1 text-sm bg-[#185E64]/50 rounded-full hover:bg-[#185E64] transition">
          {isLoginPage ? "ورود" : isRegisterPage ? "ثبت‌نام" : "ثبت‌نام"}
        </div>
      </Link>
    </nav>
  );
}