import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listStrategies } from "@/api/strategy";
import StrategySidebar from "@/components/strategy/StrategySidebar";
import StrategyDetail from "@/components/strategy/StrategyDetail";

export default function StrategyPage() {
  const [selected, setSelected] = useState<string | null>(null);

  const { data: strategies = [], isLoading } = useQuery({
    queryKey: ["strategies"],
    queryFn: listStrategies,
  });

  return (
    <div className="flex h-full">
      <StrategySidebar
        strategies={strategies}
        loading={isLoading}
        selected={selected}
        onSelect={setSelected}
      />
      <div className="flex-1 overflow-y-auto p-6">
        {selected ? (
          <StrategyDetail className={selected} />
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="text-center text-gray-500">
              <div className="mb-3 text-4xl">⚙</div>
              <p className="text-sm">
                Select a strategy from the sidebar to view its data
                requirements and build data files
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
