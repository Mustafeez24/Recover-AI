"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "./api-client";
import type { OpportunityFilters } from "./types";

// --- Queries ---

export function useDataSummary() {
  return useQuery({ queryKey: ["data-summary"], queryFn: api.getDataSummary });
}

export function useDetectionSummary() {
  return useQuery({ queryKey: ["detection-summary"], queryFn: api.getDetectionSummary });
}

export function useActionSummary() {
  return useQuery({ queryKey: ["action-summary"], queryFn: api.getActionSummary });
}

export function useAISummary() {
  return useQuery({ queryKey: ["ai-summary"], queryFn: api.getAISummary });
}

export function useOpportunities(filters: OpportunityFilters) {
  return useQuery({
    queryKey: ["opportunities", filters],
    queryFn: () => api.listOpportunities(filters),
  });
}

export function useOpportunity(id: string) {
  return useQuery({
    queryKey: ["opportunity", id],
    queryFn: () => api.getOpportunity(id),
    enabled: Boolean(id),
  });
}

export function useHistory(id: string) {
  return useQuery({
    queryKey: ["history", id],
    queryFn: () => api.getHistory(id),
    enabled: Boolean(id),
  });
}

// --- Mutations ---
//
// Every mutation here calls one existing per-case backend endpoint --
// there is no client-side bulk action and no endpoint that skips the
// plan -> validate -> execute sequence.

function useInvalidateCase(id: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["opportunity", id] });
    queryClient.invalidateQueries({ queryKey: ["history", id] });
    queryClient.invalidateQueries({ queryKey: ["opportunities"] });
    queryClient.invalidateQueries({ queryKey: ["action-summary"] });
    queryClient.invalidateQueries({ queryKey: ["detection-summary"] });
  };
}

export function usePlanAction(id: string) {
  const invalidate = useInvalidateCase(id);
  return useMutation({
    mutationFn: () => api.planAction(id),
    onSuccess: invalidate,
  });
}

export function useValidateAction(id: string) {
  const invalidate = useInvalidateCase(id);
  return useMutation({
    mutationFn: () => api.validateAction(id),
    onSuccess: invalidate,
  });
}

export function useExecuteAction(id: string) {
  const invalidate = useInvalidateCase(id);
  return useMutation({
    mutationFn: () => api.executeAction(id),
    onSuccess: invalidate,
  });
}

export function useAIRecommendation(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.getAIRecommendation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-summary"] });
    },
  });
}

export function useRunDetection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.runDetection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["detection-summary"] });
      queryClient.invalidateQueries({ queryKey: ["data-summary"] });
      queryClient.invalidateQueries({ queryKey: ["opportunities"] });
    },
  });
}

export function useRunAIBatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (batchSize: number) => api.runAIBatchAnalysis(batchSize),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-summary"] });
      queryClient.invalidateQueries({ queryKey: ["opportunities"] });
    },
  });
}
