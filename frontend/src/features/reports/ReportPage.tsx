import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";

import { ApiError } from "../../api/client";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Seo } from "../../components/Seo";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { SelectField, TextAreaField, TextField } from "../../components/ui/FormField";
import { analyzeReport } from "./api";
import { categoryOptions } from "./constants";
import { ImageUploadField } from "./ImageUploadField";
import { reportSchema } from "./reportSchema";
import type { ReportFormValues } from "./types";

const defaultValues = {
  originalDescription: "",
  location: "",
  landmark: "",
  preferredCategory: "",
  urgencyNote: "",
  citizenName: "",
  citizenContact: "",
} satisfies Partial<ReportFormValues>;

export function ReportPage() {
  const navigate = useNavigate();
  const {
    formState: { errors },
    handleSubmit,
    register,
  } = useForm<ReportFormValues>({
    defaultValues,
    resolver: zodResolver(reportSchema),
  });
  const analyze = useMutation({
    mutationFn: analyzeReport,
    onSuccess: (draft) => {
      void navigate(`/report/review/${draft.id}`);
    },
  });

  const errorMessage =
    analyze.error instanceof ApiError
      ? `${analyze.error.message}${
          analyze.error.requestId ? ` Reference: ${analyze.error.requestId}` : ""
        }`
      : analyze.error instanceof Error
        ? analyze.error.message
        : undefined;

  return (
    <section className="page-section report-page">
      <Seo
        description="Submit a photo, location, and description so CivicPulse AI can structure a public civic issue for review."
        title="Report an issue"
      />
      <div className="container report-layout">
        <div className="report-heading">
          <p className="eyebrow">Citizen reporting</p>
          <h1>Report a local issue</h1>
          <p className="page-copy">
            Add one clear photo and describe what you observed. CivicPulse AI will organize the
            report for your review before anything becomes public.
          </p>
        </div>

        <form
          className="report-form"
          onSubmit={(event) => {
            void handleSubmit((values) => analyze.mutate(values))(event);
          }}
        >
          <Card padding="large">
            <div className="form-section-heading">
              <span>1</span>
              <div>
                <h2>Issue evidence</h2>
                <p>Use a recent photo that clearly shows the civic problem.</p>
              </div>
            </div>
            <div className="form-stack">
              <ImageUploadField error={errors.image?.message} registration={register("image")} />
              <TextAreaField
                error={errors.originalDescription?.message}
                hint="Include what is wrong, who may be affected, and anything that makes it urgent."
                label="What did you observe?"
                placeholder="There is a large pothole near the school gate. Bikes are slipping and children cross here every day."
                rows={6}
                {...register("originalDescription")}
              />
            </div>
          </Card>

          <Card padding="large">
            <div className="form-section-heading">
              <span>2</span>
              <div>
                <h2>Location</h2>
                <p>Give enough context for residents and civic teams to recognize the place.</p>
              </div>
            </div>
            <div className="form-grid">
              <TextField
                error={errors.location?.message}
                label="Area or location"
                placeholder="Sector 12"
                {...register("location")}
              />
              <TextField
                error={errors.landmark?.message}
                label="Nearby landmark"
                optional
                placeholder="City Public School"
                {...register("landmark")}
              />
            </div>
          </Card>

          <Card padding="large">
            <div className="form-section-heading">
              <span>3</span>
              <div>
                <h2>Helpful context</h2>
                <p>These details are optional. AI will suggest a category and urgency.</p>
              </div>
            </div>
            <div className="form-stack">
              <SelectField
                error={errors.preferredCategory?.message}
                label="Suggested category"
                optional
                {...register("preferredCategory")}
              >
                <option value="">Let AI suggest a category</option>
                {categoryOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </SelectField>
              <TextAreaField
                error={errors.urgencyNote?.message}
                label="Urgency note"
                optional
                placeholder="For example: This is beside a hospital entrance."
                rows={3}
                {...register("urgencyNote")}
              />
            </div>
          </Card>

          <Card padding="large">
            <div className="form-section-heading">
              <span>4</span>
              <div>
                <h2>Contact details</h2>
                <p>Optional and private. These details never appear in public issue responses.</p>
              </div>
            </div>
            <div className="form-grid">
              <TextField
                error={errors.citizenName?.message}
                label="Name"
                optional
                placeholder="Your name"
                {...register("citizenName")}
              />
              <TextField
                error={errors.citizenContact?.message}
                label="Phone or email"
                optional
                placeholder="How an administrator may reach you"
                {...register("citizenContact")}
              />
            </div>
            <p className="privacy-note">
              Contact details are excluded from Gemini prompts and public APIs.
            </p>
          </Card>

          {errorMessage && (
            <ErrorState
              description={errorMessage}
              onRetry={() => void handleSubmit((values) => analyze.mutate(values))()}
              title="The report could not be analyzed"
            />
          )}

          <div className="form-submit-bar">
            <div>
              <strong>Nothing is published yet.</strong>
              <span>You will review and edit the AI result on the next screen.</span>
            </div>
            <Button isLoading={analyze.isPending} type="submit">
              Analyze with AI
            </Button>
          </div>
        </form>
      </div>
    </section>
  );
}
