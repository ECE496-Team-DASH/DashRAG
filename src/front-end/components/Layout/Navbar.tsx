import { FC } from "react";
import { useAuth } from "@/utils/AuthContext";

interface Props {
  isHome?: boolean;
}

export const Navbar: FC<Props> = ({ isHome }) => {
  const { user, token, logout } = useAuth();

  return (
    <div className="flex h-[50px] sm:h-[60px] border-b border-neutral-300 py-2 px-2 sm:px-8 items-center justify-between">
      <div className="flex items-center gap-4 font-bold text-3xl">
        DashRAG ⚡️
        {!isHome && (
          <button
            className="ml-4 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
            onClick={() => window.location.href='/'}
          >
            Go Back
          </button>
        )}
      </div>
      {token && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">{user?.email}</span>
          <button
            onClick={logout}
            className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 border border-gray-300"
          >
            Logout
          </button>
        </div>
      )}
    </div>
  );
};
