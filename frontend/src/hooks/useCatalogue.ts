import { useQuery } from "@tanstack/react-query";
import { loadCatalogue } from "../data/staticDataClient";

export const useCatalogue = () => useQuery({ queryKey: ["catalogue"], queryFn: loadCatalogue });
