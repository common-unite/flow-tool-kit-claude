// The part of the fee summary that is genuinely code: the garden's plot fee schedule.
// Kept apart from the component so it can be tested on its own and replaced without touching the form wiring.

export const RATE_BY_PLOT_SIZE = Object.freeze({
    Small: 25,
    Standard: 40,
    'Raised Bed': 55
});

// Seniors and students pay half.
export const CONCESSION_RATE = 0.5;

const roundToCents = amount => Math.round(amount * 100) / 100;

// null while answers are missing; { unpriced: true } for a plot size the schedule has no rate for.
export function plotFee({ plotSize, numberOfPlots, concession }) {
    const plots = Number(numberOfPlots);
    if (!plotSize || !Number.isInteger(plots) || plots < 1) return null;

    const rate = RATE_BY_PLOT_SIZE[plotSize];
    if (rate === undefined) return { unpriced: true, plotSize, plots };

    const subtotal = roundToCents(rate * plots);
    const discount = concession === true ? roundToCents(subtotal * CONCESSION_RATE) : 0;
    return { unpriced: false, plotSize, plots, rate, subtotal, discount, total: roundToCents(subtotal - discount) };
}
