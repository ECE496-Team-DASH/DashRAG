import { FC } from "react";

interface Props {
  isHome?: boolean;
}

export const Navbar: FC<Props> = ({ isHome }) => {
  return (
    <div className="flex w-1/2 h-[50px] sm:h-[60px] border-b border-neutral-300 py-2 px-2 sm:px-8 items-center justify-between">
      <div className="font-bold text-3xl flex items-center">
          DashRAG ⚡️
        {
          isHome ? null : (
          <button
            className="ml-24 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
            onClick={() => window.location.href='/'}
          >
            Go Back
          </button>)
        }
      </div>
    </div>
  );
};
