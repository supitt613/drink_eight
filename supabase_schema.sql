-- SQL commands to set up your Supabase tables

-- Table: public.drinks
CREATE TABLE public.drinks (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  name text NOT NULL,
  description text,
  price numeric NOT NULL,
  image_url text,
  category text,
  is_available boolean DEFAULT true,
  PRIMARY KEY (id)
);

-- RLS for drinks table
ALTER TABLE public.drinks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read access to drinks" ON public.drinks FOR SELECT USING (true);
CREATE POLICY "Allow anon insert drinks" ON public.drinks FOR INSERT WITH CHECK (true); -- For initial data population

-- Table: public.orders
CREATE TABLE public.orders (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  customer_name text NOT NULL,
  total_amount numeric NOT NULL,
  order_date timestamp with time zone DEFAULT now() NOT NULL,
  status text DEFAULT 'pending'::text NOT NULL, -- e.g., 'pending', 'completed', 'cancelled'
  PRIMARY KEY (id)
);

-- RLS for orders table
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read access to orders" ON public.orders FOR SELECT USING (true);
CREATE POLICY "Allow anon insert orders" ON public.orders FOR INSERT WITH CHECK (true);

-- Table: public.order_items
CREATE TABLE public.order_items (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  order_id uuid NOT NULL,
  drink_id uuid NOT NULL,
  quantity integer DEFAULT 1 NOT NULL,
  price_at_order numeric NOT NULL, -- Price at the time of order
  sugar_level text,
  ice_level text,
  notes text,
  PRIMARY KEY (id),
  FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE,
  FOREIGN KEY (drink_id) REFERENCES public.drinks(id) ON DELETE RESTRICT
);

-- RLS for order_items table
ALTER TABLE public.order_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read access to order_items" ON public.order_items FOR SELECT USING (true);
CREATE POLICY "Allow anon insert order_items" ON public.order_items FOR INSERT WITH CHECK (true);

-- Optional: Create an index on order_date for faster history lookups
CREATE INDEX idx_orders_order_date ON public.orders (order_date DESC);
CREATE INDEX idx_orders_customer_name ON public.orders (customer_name);
