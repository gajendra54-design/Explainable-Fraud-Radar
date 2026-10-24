import { test, expect } from "@playwright/test";
// Start the API and Vite before running. Credentials come from local configuration only.
test("investigator can inspect evidence and record an auditable decision", async ({
  page,
}) => {
  const username = process.env.RADAR_E2E_USER;
  const password = process.env.RADAR_E2E_PASSWORD;
  test.skip(
    !username || !password,
    "Set RADAR_E2E_USER and RADAR_E2E_PASSWORD",
  );
  await page.goto(process.env.RADAR_E2E_URL || "http://127.0.0.1:5177");
  await page.getByLabel("Username", { exact: true }).fill(username!);
  await page.getByLabel("Password", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Enter workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "A clearer view of risk." }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Transaction activity" }),
  ).toBeVisible();
  await page.screenshot({
    path: "../reports/screenshots/overview.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Transactions", exact: true }).click();
  await page.getByLabel("Risk band", { exact: true }).selectOption("Critical");
  await page.getByLabel("Sort by").selectOption("risk_score");
  await page.locator("tbody .text-link").first().click();
  await expect(
    page.getByRole("heading", { name: "What influenced this prediction?" }),
  ).toBeVisible();
  await expect(
    page.getByText("Exact logistic linear attribution", { exact: false }),
  ).toBeVisible();
  await page.screenshot({
    path: "../reports/screenshots/explanation.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Investigations", exact: true })
    .click();
  await page.getByLabel("Case status").selectOption("New");
  await page.locator("tbody .text-link").first().click();
  await page
    .getByLabel("Assign investigator", { exact: true })
    .selectOption(username!);
  await page.getByRole("button", { name: "Assign", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Start review" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Start review" }).click();
  await page
    .getByLabel("Investigation note")
    .fill(
      "Automated E2E review: synthetic evidence inspected; no enforcement action.",
    );
  await page.getByRole("button", { name: "Add note" }).click();
  await expect(page.getByText("note added", { exact: true })).toBeVisible();
  await page.getByLabel("Record a disposition").selectOption("Inconclusive");
  await page.getByRole("button", { name: "Review & resolve" }).click();
  await page.getByRole("button", { name: "Confirm decision" }).click();
  await expect(
    page.getByText("disposition recorded", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Model evaluation", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Model comparison" }),
  ).toBeVisible();
  const prPanel = page
    .locator("section")
    .filter({
      has: page.getByRole("heading", {
        name: "Precision–recall curve",
        exact: true,
      }),
    });
  await expect(prPanel.locator("path.recharts-line-curve")).toHaveAttribute(
    "d",
    /M.+/,
  );
  await page.screenshot({
    path: "../reports/screenshots/evaluation.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Monitoring", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Feature distribution monitoring" }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(page.locator("tbody tr").first()).toBeVisible();
  await page.screenshot({
    path: "../reports/screenshots/monitoring.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page.screenshot({
    path: "../reports/screenshots/mobile.png",
    fullPage: true,
  });
});
