import Link from "next/link";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/about", label: "About" },
  { href: "/projects", label: "Projects" },
  { href: "/blog", label: "Blog" },
];

export default function Navbar() {
  return (
    <header className="border-b border-gray-200 bg-white">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-8 py-5">
        <Link href="/" className="text-lg font-bold tracking-tight">
          Ruiyuan
        </Link>

        <div className="flex gap-8 text-sm font-medium text-gray-600">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href} className="hover:text-black">
              {item.label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}