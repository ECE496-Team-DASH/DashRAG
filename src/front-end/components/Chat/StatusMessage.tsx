import { FC } from "react";

interface Props {
  status: "uploading" | "processing" | "ready" | "error";
  message: string;
  progress?: number;
}

export const StatusMessage: FC<Props> = ({ status, message, progress }) => {
  const getIcon = () => {
    switch (status) {
      case "uploading":
        return "📤";
      case "processing":
        return "⚙️";
      case "ready":
        return "✅";
      case "error":
        return "❌";
      default:
        return "ℹ️";
    }
  };

  const getBackgroundColor = () => {
    switch (status) {
      case "uploading":
        return "bg-blue-50 border-blue-200";
      case "processing":
        return "bg-yellow-50 border-yellow-200";
      case "ready":
        return "bg-green-50 border-green-200";
      case "error":
        return "bg-red-50 border-red-200";
      default:
        return "bg-gray-50 border-gray-200";
    }
  };

  const getTextColor = () => {
    switch (status) {
      case "uploading":
        return "text-blue-800";
      case "processing":
        return "text-yellow-800";
      case "ready":
        return "text-green-800";
      case "error":
        return "text-red-800";
      default:
        return "text-gray-800";
    }
  };

  return (
    <div className="flex justify-center my-3">
      <div
        className={`${getBackgroundColor()} ${getTextColor()} border rounded-lg px-4 py-3 text-sm flex items-center gap-3 max-w-[85%] shadow-sm`}
      >
        <span className="text-xl flex-shrink-0">{getIcon()}</span>
        <div className="flex-1">
          <div>{message}</div>
          {progress !== undefined && status === "processing" && (
            <div className="mt-2">
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-white rounded-full h-2 overflow-hidden border border-yellow-300">
                  <div
                    className="h-full bg-gradient-to-r from-yellow-400 to-yellow-600 transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="text-xs font-semibold min-w-[3rem] text-right">
                  {progress}%
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
