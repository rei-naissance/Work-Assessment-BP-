import { z } from 'zod';

export const homeIdentitySchema = z.object({
  address_line1: z.string().optional(),
  address_line2: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  zip_code: z.string().regex(/^\d{5}(-\d{4})?$/, 'Enter a valid ZIP code'),
  home_type: z.string().min(1, 'Select a home type'),
  year_built: z.number().min(1800).max(new Date().getFullYear()).nullable(),
  square_feet: z.number().min(100).max(100000).nullable(),
  home_nickname: z.string().optional(),
  owner_renter: z.enum(['owner', 'renter']).optional(),
});

export const emergencyContactSchema = z.object({
  name: z.string(),
  phone: z.string(),
  relationship: z.string(),
});

export const serviceProviderSchema = z.object({
  name: z.string(),
  phone: z.string(),
});

export const utilityProviderSchema = z.object({
  company: z.string(),
  account_number: z.string(),
  phone: z.string(),
});

export const insuranceInfoSchema = z.object({
  provider: z.string(),
  policy_number: z.string(),
  claim_phone: z.string(),
});

export const emailSchema = z.string().email('Enter a valid email');
export const otpSchema = z.string().length(6, 'OTP must be 6 digits');
